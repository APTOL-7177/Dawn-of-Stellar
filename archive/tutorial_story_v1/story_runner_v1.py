"""
플레이어블 스토리 튜토리얼 시스템
Dawn of Stellar - 시공의 여명

YAML 기반 스토리 챕터 + 실제 플레이어블 던전/전투
"""

import tcod
import tcod.console
import tcod.event
import time
import yaml
import random
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, field
from enum import Enum

from src.core.logger import get_logger, Loggers
from src.core.event_bus import event_bus
from src.audio import play_bgm, play_sfx
from src.ui.input_handler import InputHandler, GameAction


# =============================================================================
# YAML 스토리 로더
# =============================================================================

STORY_PATH = Path("data/tutorials/courses")

# BGM 매핑 (config.yaml 기반)
BGM_MAP = {
    "prologue": "intro_",
    "story": "menu",
    "npc_meet": "menu2",
    "party_setup": "party_setup",
    "town": "town",
    "dungeon": "dungeon_normal",  # caves는 dungeon_normal로 매핑됨
    "battle": "battle",
    "boss": "boss",
    "victory": "fanfare",
}


def load_story_config() -> Dict[str, Any]:
    """스토리 코스 설정 로드"""
    config_path = STORY_PATH / "story_course_config.yaml"
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    except Exception as e:
        logger.error(f"스토리 설정 로드 실패: {e}")
        return {}


def load_tutorial_yaml(tutorial_id: str) -> Dict[str, Any]:
    """개별 튜토리얼 YAML 로드"""
    yaml_path = STORY_PATH / f"{tutorial_id}.yaml"
    try:
        with open(yaml_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    except Exception as e:
        logger.warning(f"튜토리얼 로드 실패 ({tutorial_id}): {e}")
        return {}


def safe_play_bgm(bgm_key: str):
    """안전한 BGM 재생 (매핑 사용)"""
    actual_bgm = BGM_MAP.get(bgm_key, bgm_key)
    try:
        play_bgm(actual_bgm, loop=True, fade_in=True)
    except Exception as e:
        logger.warning(f"BGM 재생 실패 ({bgm_key}): {e}")

# 튜토리얼 던전 & 탐험 시스템
from src.tutorial.tutorial_dungeon import TutorialDungeon
from src.world.exploration import ExplorationSystem
from src.world.tile import TileType

# 캐릭터 & 인벤토리
from src.character.character import Character
from src.equipment.inventory import Inventory

# 전투 시스템
from src.combat.combat_manager import CombatManager, CombatState
from src.world.enemy_generator import SimpleEnemy, EnemyTemplate


logger = get_logger(Loggers.SYSTEM)


# =============================================================================
# 색상 상수
# =============================================================================

class Colors:
    """UI 색상"""
    TITLE = (255, 215, 0)
    NPC_SELENA = (0, 200, 255)
    NPC_KARNOS = (255, 100, 100)
    NORMAL = (255, 255, 255)
    HINT = (150, 150, 150)
    SUCCESS = (0, 255, 0)
    WARNING = (255, 255, 0)
    ERROR = (255, 0, 0)
    OBJECTIVE = (0, 255, 255)
    PLAYER = (255, 255, 0)
    ENEMY = (255, 50, 50)
    WALL = (100, 100, 100)
    FLOOR = (50, 50, 50)
    EXIT = (0, 255, 0)


NPC_COLORS = {
    "selena": Colors.NPC_SELENA,
    "karnos": Colors.NPC_KARNOS,
}

NPC_NAMES = {
    "selena": "셀레나",
    "karnos": "카르노스",
}


# =============================================================================
# 튜토리얼 상태
# =============================================================================

class TutorialPhase(Enum):
    """튜토리얼 단계"""
    PROLOGUE = "prologue"
    MOVEMENT = "movement"
    COMBAT = "combat"
    SKILLS = "skills"
    COMPLETE = "complete"


@dataclass
class TutorialProgress:
    """튜토리얼 진행 상태"""
    phase: TutorialPhase = TutorialPhase.PROLOGUE
    movement_completed: bool = False
    combat_completed: bool = False
    skills_completed: bool = False
    selected_job: Optional[str] = None
    stellar_fragments: int = 0


# =============================================================================
# 대화 시스템
# =============================================================================

class DialogueSystem:
    """NPC 대화 시스템"""
    
    def __init__(self, console: tcod.console.Console, context: tcod.context.Context):
        self.console = console
        self.context = context
    
    def show_dialogue(self, speaker: str, text: str, 
                      color: Tuple[int, int, int] = None,
                      typing_effect: bool = True) -> bool:
        """
        대화 표시
        
        Returns:
            True: 계속, False: 스킵
        """
        self.console.clear()
        
        # 화자 이름
        speaker_name = NPC_NAMES.get(speaker, speaker)
        speaker_color = color or NPC_COLORS.get(speaker, Colors.NORMAL)
        
        # 대화 박스 위치
        box_width = min(60, self.console.width - 10)
        box_x = (self.console.width - box_width) // 2
        box_y = self.console.height // 2 - 3
        
        # 화자 표시
        name_text = f"[ {speaker_name} ]"
        self.console.print(
            (self.console.width - len(name_text)) // 2,
            box_y - 2,
            name_text,
            fg=speaker_color
        )
        
        # 대화 박스
        self.console.draw_frame(
            box_x - 1, box_y - 1,
            box_width + 2, 5,
            fg=(80, 80, 80),
            bg=(20, 20, 30)
        )
        
        # 텍스트 출력
        if typing_effect:
            result = self._type_text(text, box_x, box_y, box_width, Colors.NORMAL)
            if not result:
                return False
        else:
            wrapped = self._wrap_text(text, box_width - 2)
            for i, line in enumerate(wrapped[:3]):
                self.console.print(box_x, box_y + i, line, fg=Colors.NORMAL)
        
        # 안내
        hint = "[Z] 계속  [ESC] 건너뛰기"
        self.console.print(
            (self.console.width - len(hint)) // 2,
            self.console.height - 3,
            hint,
            fg=Colors.HINT
        )
        
        self.context.present(self.console)
        
        # 입력 대기
        return self._wait_for_continue()
    
    def _type_text(self, text: str, x: int, y: int, max_width: int, 
                   color: Tuple[int, int, int]) -> bool:
        """타이핑 효과"""
        wrapped = self._wrap_text(text, max_width - 2)
        
        for line_idx, line in enumerate(wrapped[:3]):
            for char_idx, char in enumerate(line):
                # 이벤트 체크
                for event in tcod.event.get():
                    if isinstance(event, tcod.event.KeyDown):
                        if event.sym == tcod.event.KeySym.ESCAPE:
                            return False
                        elif event.sym in (tcod.event.KeySym.z, tcod.event.KeySym.RETURN):
                            # 빠른 완성
                            for ri, rl in enumerate(wrapped[:3]):
                                self.console.print(x, y + ri, rl, fg=color)
                            self.context.present(self.console)
                            return True
                
                self.console.print(x + char_idx, y + line_idx, char, fg=color)
                self.context.present(self.console)
                time.sleep(0.02)
        
        return True
    
    def _wrap_text(self, text: str, max_width: int) -> List[str]:
        """텍스트 줄바꿈"""
        words = text.split()
        lines = []
        current = ""
        
        for word in words:
            test = f"{current} {word}".strip()
            if len(test) <= max_width:
                current = test
            else:
                if current:
                    lines.append(current)
                current = word
        
        if current:
            lines.append(current)
        
        return lines if lines else [""]
    
    def _wait_for_continue(self) -> bool:
        """입력 대기 (디바운싱 적용)"""
        # 이벤트 버퍼 비우기 + 디바운싱 (Z 연타 방지)
        time.sleep(0.3)
        for _ in tcod.event.get():
            pass
        
        while True:
            for event in tcod.event.wait():
                if isinstance(event, tcod.event.KeyDown):
                    if event.sym in (tcod.event.KeySym.z, tcod.event.KeySym.RETURN,
                                     tcod.event.KeySym.SPACE):
                        return True
                    elif event.sym == tcod.event.KeySym.ESCAPE:
                        return False
                elif isinstance(event, tcod.event.Quit):
                    return False


# =============================================================================
# 메시지 렌더러
# =============================================================================

class MessageRenderer:
    """메시지 렌더러"""
    
    def __init__(self, console: tcod.console.Console, context: tcod.context.Context):
        self.console = console
        self.context = context
    
    def show_title(self, title: str, subtitle: str = "") -> bool:
        """타이틀 화면"""
        self.console.clear()
        
        self.console.print(
            (self.console.width - len(title)) // 2,
            self.console.height // 2 - 2,
            title,
            fg=Colors.TITLE
        )
        
        if subtitle:
            self.console.print(
                (self.console.width - len(subtitle)) // 2,
                self.console.height // 2,
                subtitle,
                fg=Colors.NORMAL
            )
        
        hint = "[Z] 계속  [ESC] 건너뛰기"
        self.console.print(
            (self.console.width - len(hint)) // 2,
            self.console.height - 5,
            hint,
            fg=Colors.HINT
        )
        
        self.context.present(self.console)
        return self._wait_input()
    
    def show_objective(self, objective: str) -> bool:
        """목표 표시"""
        self.console.clear()
        
        header = "=== 목표 ==="
        self.console.print(
            (self.console.width - len(header)) // 2,
            self.console.height // 2 - 2,
            header,
            fg=Colors.WARNING
        )
        
        self.console.print(
            (self.console.width - len(objective)) // 2,
            self.console.height // 2,
            objective,
            fg=Colors.OBJECTIVE
        )
        
        hint = "[Z] 시작"
        self.console.print(
            (self.console.width - len(hint)) // 2,
            self.console.height // 2 + 4,
            hint,
            fg=Colors.HINT
        )
        
        self.context.present(self.console)
        return self._wait_input()
    
    def show_completion(self, message: str, reward: int = 0) -> bool:
        """완료 화면"""
        self.console.clear()
        
        self.console.print(
            (self.console.width - len(message)) // 2,
            self.console.height // 2 - 2,
            message,
            fg=Colors.SUCCESS
        )
        
        if reward > 0:
            reward_text = f"★ 별의 파편 +{reward}"
            self.console.print(
                (self.console.width - len(reward_text)) // 2,
                self.console.height // 2 + 1,
                reward_text,
                fg=Colors.TITLE
            )
        
        try:
            play_sfx("me", "Fanfare1")
        except:
            pass
        
        hint = "[Z] 계속"
        self.console.print(
            (self.console.width - len(hint)) // 2,
            self.console.height // 2 + 5,
            hint,
            fg=Colors.HINT
        )
        
        self.context.present(self.console)
        return self._wait_input()
    
    def _wait_input(self) -> bool:
        """입력 대기"""
        time.sleep(0.1)
        for _ in tcod.event.get():
            pass
        
        while True:
            for event in tcod.event.wait():
                if isinstance(event, tcod.event.KeyDown):
                    if event.sym in (tcod.event.KeySym.RETURN, tcod.event.KeySym.z):
                        return True
                    elif event.sym == tcod.event.KeySym.ESCAPE:
                        return False
                elif isinstance(event, tcod.event.Quit):
                    return False


# =============================================================================
# 이동 튜토리얼
# =============================================================================

class MovementTutorial:
    """실제 이동 튜토리얼"""
    
    def __init__(self, console: tcod.console.Console, context: tcod.context.Context,
                 party: List[Character], inventory: Inventory):
        self.console = console
        self.context = context
        self.party = party
        self.inventory = inventory
        self.input_handler = InputHandler()
    
    def run(self) -> bool:
        """
        이동 튜토리얼 실행
        
        Returns:
            True: 완료, False: 스킵
        """
        logger.info("이동 튜토리얼 시작")
        
        # 튜토리얼 던전 생성
        dungeon = TutorialDungeon.create_movement_tutorial()
        
        # 탐험 시스템 초기화
        exploration = ExplorationSystem(
            dungeon, self.party, floor_number=0, inventory=self.inventory
        )
        start_x, start_y = dungeon.start_pos
        exploration.player.x = start_x
        exploration.player.y = start_y
        
        # 목표 지점
        target_x, target_y = dungeon.exit_pos
        
        while True:
            # 렌더링
            self.console.clear()
            self._render_map(exploration, target_x, target_y)
            
            # 가이드
            guide = "방향키(↑↓←→) 또는 WASD로 ★ 표시된 출구까지 이동하세요!"
            self.console.print(2, 2, guide, fg=Colors.WARNING)
            
            pos_msg = f"현재 위치: ({exploration.player.x}, {exploration.player.y})"
            self.console.print(2, 3, pos_msg, fg=Colors.HINT)
            
            self.console.print(2, self.console.height - 2, "[ESC] 건너뛰기", fg=Colors.HINT)
            
            self.context.present(self.console)
            
            # 입력 처리
            for event in tcod.event.wait():
                action = self.input_handler.dispatch(event)
                
                if action == GameAction.ESCAPE:
                    return False
                elif action in (GameAction.MOVE_UP, GameAction.MOVE_DOWN,
                               GameAction.MOVE_LEFT, GameAction.MOVE_RIGHT):
                    dx, dy = 0, 0
                    if action == GameAction.MOVE_UP:
                        dy = -1
                    elif action == GameAction.MOVE_DOWN:
                        dy = 1
                    elif action == GameAction.MOVE_LEFT:
                        dx = -1
                    elif action == GameAction.MOVE_RIGHT:
                        dx = 1
                    
                    # 이동 가능 여부 확인
                    new_x = exploration.player.x + dx
                    new_y = exploration.player.y + dy
                    
                    if (0 <= new_x < dungeon.width and 
                        0 <= new_y < dungeon.height and
                        dungeon.tiles[new_y][new_x].walkable):
                        exploration.player.x = new_x
                        exploration.player.y = new_y
                        
                        # 목표 도달 확인
                        if new_x == target_x and new_y == target_y:
                            logger.info("이동 튜토리얼 완료")
                            return True
                
                elif isinstance(event, tcod.event.Quit):
                    return False
    
    def _render_map(self, exploration: ExplorationSystem, target_x: int, target_y: int):
        """맵 렌더링"""
        dungeon = exploration.dungeon
        player_x, player_y = exploration.player.x, exploration.player.y
        
        map_start_x = 5
        map_start_y = 6
        
        for y in range(dungeon.height):
            for x in range(dungeon.width):
                tile = dungeon.tiles[y][x]
                screen_x = map_start_x + x
                screen_y = map_start_y + y
                
                if screen_x >= self.console.width or screen_y >= self.console.height:
                    continue
                
                if x == player_x and y == player_y:
                    char, color = "@", Colors.PLAYER
                elif x == target_x and y == target_y:
                    char, color = "★", Colors.EXIT
                elif not tile.walkable:
                    char, color = "#", Colors.WALL
                else:
                    char, color = ".", Colors.FLOOR
                
                self.console.print(screen_x, screen_y, char, fg=color)


# =============================================================================
# 전투 튜토리얼
# =============================================================================

class CombatTutorial:
    """실제 전투 튜토리얼"""
    
    def __init__(self, console: tcod.console.Console, context: tcod.context.Context,
                 party: List[Character], inventory: Inventory):
        self.console = console
        self.context = context
        self.party = party
        self.inventory = inventory
        self.dialogue = DialogueSystem(console, context)
        self.message = MessageRenderer(console, context)
    
    def run(self) -> bool:
        """
        전투 튜토리얼 실행
        
        Returns:
            True: 완료, False: 스킵
        """
        logger.info("전투 튜토리얼 시작")
        
        # 전투 설명
        if not self._show_combat_intro():
            return False
        
        # 실제 전투 실행
        result = self._run_actual_combat()
        
        return result
    
    def _show_combat_intro(self) -> bool:
        """전투 설명"""
        dialogues = [
            ("karnos", "이제 전투를 배울 차례다."),
            ("karnos", "ATB 게이지가 차면 행동 메뉴가 열린다."),
            ("karnos", "방향키로 메뉴 선택, Z로 확인이다."),
            ("karnos", "'BRV 공격'으로 적의 BRV를 깎고 내 BRV를 축적해라."),
            ("karnos", "BRV가 충분하면 'HP 공격'으로 실제 데미지를 준다."),
            ("karnos", "적의 BRV를 0으로 만들면 'BREAK'! 추가 피해를 줄 수 있다."),
            ("karnos", "직접 해봐라. 앞에 있는 왜곡체를 처치해봐.")
        ]
        
        for speaker, text in dialogues:
            if not self.dialogue.show_dialogue(speaker, text):
                return False
        
        return True
    
    def _run_actual_combat(self) -> bool:
        """실제 전투 실행"""
        from src.ui.combat_ui import run_combat
        
        # 전투 BGM
        safe_play_bgm("battle")
        
        try:
            # 튜토리얼용 약한 적 생성
            enemies = []
            try:
                # 튜토리얼용 약한 적 템플릿 생성
                template = EnemyTemplate(
                    enemy_id="tutorial_anomaly",
                    name="시간 왜곡체",
                    level=1,
                    hp=50,
                    mp=10,
                    physical_attack=5,
                    physical_defense=2,
                    magic_attack=5,
                    magic_defense=2,
                    speed=50,
                    max_brv=100,
                    init_brv=50,
                    luck=10,
                    accuracy=80,
                    evasion=5
                )
                enemy = SimpleEnemy(template, level_modifier=1.0)
                enemies.append(enemy)
                logger.info(f"튜토리얼 적 생성: {enemy.name} HP={enemy.current_hp}")
            except Exception as e:
                logger.error(f"튜토리얼 적 생성 실패: {e}")
            
            if not enemies:
                logger.error("적 생성 실패")
                return True  # 실패해도 진행
            
            # 전투 실행
            result, game_over = run_combat(
                self.console,
                self.context,
                self.party,
                enemies,
                self.inventory
            )
            
            logger.info(f"전투 결과: {result}, 게임오버: {game_over}")
            
            # 전투 후 대화
            if result == CombatState.VICTORY:
                safe_play_bgm("story")
                self.dialogue.show_dialogue("karnos", "훌륭하다! BRV 시스템을 이해했군.")
                return True
            elif result == CombatState.FLED:
                safe_play_bgm("story")
                self.dialogue.show_dialogue("karnos", "도망쳤군... 다음에는 끝까지 싸워봐라.")
                return True  # 도망해도 진행
            else:
                safe_play_bgm("story")
                # 패배해도 부활 후 진행
                for char in self.party:
                    char.current_hp = char.max_hp
                self.dialogue.show_dialogue("karnos", "괜찮다. 다시 일어서면 된다.")
                return True
                
        except Exception as e:
            logger.error(f"전투 실행 오류: {e}")
            safe_play_bgm("story")
            return True


# =============================================================================
# 스토리 던전 탐험 (실전처럼 플레이, 절대 실패 불가)
# =============================================================================

class StoryDungeonExplorer:
    """
    스토리 전용 던전 탐험
    
    실제 게임처럼 플레이하지만:
    - 적이 매우 약함
    - 패배해도 즉시 부활
    - 회복 포인트 많음
    - NPC 힌트 제공
    """
    
    def __init__(self, console: tcod.console.Console, context: tcod.context.Context,
                 party: List[Character], inventory: Inventory):
        self.console = console
        self.context = context
        self.party = party
        self.inventory = inventory
        self.input_handler = InputHandler()
        self.dialogue = DialogueSystem(console, context)
        self.message = MessageRenderer(console, context)
        
        # 던전 상태
        self.dungeon = None
        self.markers = []
        self.exploration = None
        self.defeated_enemies = set()  # 처치한 적 위치
    
    def run(self) -> bool:
        """
        스토리 던전 탐험 실행
        
        Returns:
            True: 완료, False: 스킵
        """
        from src.tutorial.tutorial_dungeon import TutorialDungeon, StoryMapMarker
        
        logger.info("스토리 던전 탐험 시작")
        
        # 스토리 던전 생성
        self.dungeon, self.markers = TutorialDungeon.create_story_dungeon()
        
        # 탐험 시스템 초기화
        self.exploration = ExplorationSystem(
            self.dungeon, self.party, floor_number=0, inventory=self.inventory
        )
        start_x, start_y = self.dungeon.start_pos
        self.exploration.player.x = start_x
        self.exploration.player.y = start_y
        
        # 목표
        exit_x, exit_y = self.dungeon.exit_pos
        
        # BGM
        safe_play_bgm("dungeon")
        
        # 시작 대화
        self.dialogue.show_dialogue("selena", "여기는 시간의 균열이에요. 조심하세요!")
        
        while True:
            # 렌더링
            self.console.clear()
            self._render_dungeon(exit_x, exit_y)
            
            # HUD
            self._render_hud()
            
            self.context.present(self.console)
            
            # 입력 처리
            for event in tcod.event.wait():
                action = self.input_handler.dispatch(event)
                
                if action == GameAction.ESCAPE:
                    return False
                
                elif action in (GameAction.MOVE_UP, GameAction.MOVE_DOWN,
                               GameAction.MOVE_LEFT, GameAction.MOVE_RIGHT):
                    dx, dy = 0, 0
                    if action == GameAction.MOVE_UP:
                        dy = -1
                    elif action == GameAction.MOVE_DOWN:
                        dy = 1
                    elif action == GameAction.MOVE_LEFT:
                        dx = -1
                    elif action == GameAction.MOVE_RIGHT:
                        dx = 1
                    
                    # 이동
                    new_x = self.exploration.player.x + dx
                    new_y = self.exploration.player.y + dy
                    
                    if self._can_move(new_x, new_y):
                        self.exploration.player.x = new_x
                        self.exploration.player.y = new_y
                        
                        # 마커 이벤트 확인
                        self._check_marker_events(new_x, new_y)
                        
                        # 출구 도달
                        if new_x == exit_x and new_y == exit_y:
                            self.dialogue.show_dialogue("selena", "출구에 도착했어요! 훌륭해요!")
                            return True
                
                elif isinstance(event, tcod.event.Quit):
                    return False
    
    def _can_move(self, x: int, y: int) -> bool:
        """이동 가능 여부"""
        if 0 <= x < self.dungeon.width and 0 <= y < self.dungeon.height:
            return self.dungeon.tiles[y][x].walkable
        return False
    
    def _check_marker_events(self, x: int, y: int):
        """마커 이벤트 확인"""
        for marker in self.markers:
            if marker.x == x and marker.y == y:
                if marker.marker_type == "npc":
                    self._handle_npc(marker)
                elif marker.marker_type == "enemy":
                    self._handle_enemy(marker)
                elif marker.marker_type == "heal":
                    self._handle_heal(marker)
    
    def _handle_npc(self, marker):
        """NPC 대화"""
        npc_name = marker.data.get("name", "")
        dialogue = marker.data.get("dialogue", "...")
        self.dialogue.show_dialogue(npc_name, dialogue)
    
    def _handle_enemy(self, marker):
        """적 조우"""
        pos_key = (marker.x, marker.y)
        if pos_key in self.defeated_enemies:
            return  # 이미 처치
        
        enemy_name = marker.data.get("name", "적")
        enemy_hp = marker.data.get("hp", 30)
        enemy_brv = marker.data.get("brv", 40)
        enemy_attack = marker.data.get("attack", 3)
        
        # 전투 시작 메시지
        self.message.show_objective(f"⚔ {enemy_name} 출현!")
        
        # 전투 BGM
        safe_play_bgm("battle")
        
        # 적 생성
        from src.ui.combat_ui import run_combat
        
        template = EnemyTemplate(
            enemy_id="story_enemy",
            name=enemy_name,
            level=1,
            hp=enemy_hp,
            mp=10,
            physical_attack=enemy_attack,
            physical_defense=1,
            magic_attack=enemy_attack,
            magic_defense=1,
            speed=40,
            max_brv=enemy_brv,
            init_brv=enemy_brv // 2,
            luck=5,
            accuracy=70,
            evasion=3
        )
        enemy = SimpleEnemy(template, level_modifier=1.0)
        
        # 전투 실행
        result, _ = run_combat(
            self.console, self.context,
            self.party, [enemy], self.inventory
        )
        
        # 던전 BGM 복귀
        safe_play_bgm("dungeon")
        
        if result == CombatState.VICTORY:
            self.defeated_enemies.add(pos_key)
            self.dialogue.show_dialogue("karnos", "잘했다!")
        else:
            # 패배해도 부활
            for char in self.party:
                char.current_hp = char.max_hp
                char.current_mp = char.max_mp
            self.dialogue.show_dialogue("selena", "괜찮아요, 다시 해봐요!")
    
    def _handle_heal(self, marker):
        """회복"""
        for char in self.party:
            char.current_hp = char.max_hp
            char.current_mp = char.max_mp
        
        try:
            play_sfx("combat", "heal")
        except:
            pass
        
        # 간단한 회복 메시지 (대화창 없이)
        self.console.print(2, 2, "♥ HP/MP 회복!", fg=Colors.SUCCESS)
        self.context.present(self.console)
        time.sleep(0.5)
    
    def _render_dungeon(self, exit_x: int, exit_y: int):
        """던전 렌더링"""
        player_x = self.exploration.player.x
        player_y = self.exploration.player.y
        
        map_start_x = 5
        map_start_y = 5
        
        for y in range(self.dungeon.height):
            for x in range(self.dungeon.width):
                screen_x = map_start_x + x
                screen_y = map_start_y + y
                
                if screen_x >= self.console.width - 5 or screen_y >= self.console.height - 5:
                    continue
                
                # 마커 확인
                marker_char = None
                marker_color = None
                for m in self.markers:
                    if m.x == x and m.y == y:
                        if m.marker_type == "npc":
                            marker_char, marker_color = "N", Colors.NPC_SELENA
                        elif m.marker_type == "enemy" and (x, y) not in self.defeated_enemies:
                            marker_char, marker_color = "E", Colors.ENEMY
                        elif m.marker_type == "heal":
                            marker_char, marker_color = "+", Colors.SUCCESS
                        break
                
                tile = self.dungeon.tiles[y][x]
                
                if x == player_x and y == player_y:
                    char, color = "@", Colors.PLAYER
                elif x == exit_x and y == exit_y:
                    char, color = "★", Colors.EXIT
                elif marker_char:
                    char, color = marker_char, marker_color
                elif not tile.walkable:
                    char, color = "#", Colors.WALL
                else:
                    char, color = ".", Colors.FLOOR
                
                self.console.print(screen_x, screen_y, char, fg=color)
    
    def _render_hud(self):
        """HUD 렌더링"""
        # 조작 안내
        self.console.print(2, 2, "방향키: 이동  |  E: 적  |  +: 회복  |  N: NPC", fg=Colors.HINT)
        
        # 파티 상태
        y = self.console.height - 4
        for char in self.party:
            hp_text = f"{char.name}: HP {char.current_hp}/{char.max_hp}"
            self.console.print(2, y, hp_text, fg=Colors.NORMAL)
            y += 1
        
        self.console.print(2, self.console.height - 2, "[ESC] 건너뛰기", fg=Colors.HINT)


# =============================================================================
# 메인 스토리 튜토리얼 러너
# =============================================================================

class StoryTutorialRunner:
    """플레이어블 스토리 튜토리얼 메인 러너"""
    
    def __init__(self, console: tcod.console.Console, context: tcod.context.Context):
        self.console = console
        self.context = context
        
        # 튜토리얼용 파티 (전사 1명)
        self.tutorial_char = Character("수련생", "warrior", level=1)
        self.party = [self.tutorial_char]
        
        # 인벤토리
        self.inventory = Inventory(base_weight=100.0, party=self.party)
        
        # 서브 시스템
        self.dialogue = DialogueSystem(console, context)
        self.message = MessageRenderer(console, context)
        
        # 진행 상태
        self.progress = TutorialProgress()
    
    def run(self) -> Dict[str, Any]:
        """
        스토리 튜토리얼 실행
        
        Returns:
            결과 딕셔너리
        """
        result = {
            "completed": False,
            "job_unlocked": None,
            "rewards": {"stellar_fragments": 0}
        }
        
        logger.info("=== 스토리 튜토리얼 시작 ===")
        
        # 1. 프롤로그
        safe_play_bgm("prologue")
        if not self._run_prologue():
            return result
        
        # 2. 이동 튜토리얼 (기초)
        safe_play_bgm("story")
        if not self._run_movement_phase():
            return result
        
        self.progress.movement_completed = True
        self.progress.stellar_fragments += 20
        
        # 3. 전투 튜토리얼 (기초)
        if not self._run_combat_phase():
            return result
        
        self.progress.combat_completed = True
        self.progress.stellar_fragments += 30
        
        # 4. 스토리 던전 탐험 (실전)
        if not self._run_story_dungeon():
            return result
        
        self.progress.stellar_fragments += 50
        
        # 5. 스킬 설명
        if not self._run_skills_phase():
            return result
        
        self.progress.skills_completed = True
        self.progress.stellar_fragments += 50
        
        # 5. 완료
        self._show_final_completion()
        
        result["completed"] = True
        result["job_unlocked"] = "time_mage"
        result["rewards"]["stellar_fragments"] = self.progress.stellar_fragments
        
        # 보상 적용
        self._apply_rewards(result)
        
        # 메인메뉴 BGM
        safe_play_bgm("story")
        
        logger.info("=== 스토리 튜토리얼 완료 ===")
        return result
    
    def _run_prologue(self) -> bool:
        """프롤로그"""
        self.progress.phase = TutorialPhase.PROLOGUE
        
        if not self.message.show_title("Dawn of Stellar", "시공의 여명"):
            return False
        
        dialogues = [
            ("selena", "...눈을 떠요. 당신은 선택받았어요."),
            ("selena", "시공 균열이 세계를 집어삼키고 있어요."),
            ("selena", "당신만이 이 세계를 구할 수 있어요."),
            ("selena", "저는 셀레나, 당신을 안내할 시간의 정령이에요."),
            ("selena", "먼저 기본적인 것들부터 알려드릴게요.")
        ]
        
        for speaker, text in dialogues:
            if not self.dialogue.show_dialogue(speaker, text):
                return False
        
        return True
    
    def _run_movement_phase(self) -> bool:
        """이동 튜토리얼 단계"""
        self.progress.phase = TutorialPhase.MOVEMENT
        
        if not self.message.show_objective("목표: 출구(★)까지 이동하세요"):
            return False
        
        movement = MovementTutorial(
            self.console, self.context, self.party, self.inventory
        )
        
        if not movement.run():
            return False
        
        return self.message.show_completion("이동 튜토리얼 완료!", 20)
    
    def _run_combat_phase(self) -> bool:
        """전투 튜토리얼 단계"""
        self.progress.phase = TutorialPhase.COMBAT
        
        combat = CombatTutorial(
            self.console, self.context, self.party, self.inventory
        )
        
        if not combat.run():
            return False
        
        return self.message.show_completion("전투 튜토리얼 완료!", 30)
    
    def _run_story_dungeon(self) -> bool:
        """스토리 던전 탐험 (실전)"""
        # 체력 회복
        for char in self.party:
            char.current_hp = char.max_hp
            char.current_mp = char.max_mp
        
        # 소개
        dialogues = [
            ("selena", "이제 실전이에요!"),
            ("selena", "시간의 균열 안을 탐험하며 적과 싸워요."),
            ("karnos", "걱정 마라. 내가 지켜보고 있다."),
            ("karnos", "패배해도 즉시 부활할 수 있으니 마음껏 싸워봐라.")
        ]
        
        for speaker, text in dialogues:
            if not self.dialogue.show_dialogue(speaker, text):
                return False
        
        if not self.message.show_objective("목표: 시간의 균열 탈출!"):
            return False
        
        # 스토리 던전 탐험
        dungeon_explorer = StoryDungeonExplorer(
            self.console, self.context, self.party, self.inventory
        )
        
        if not dungeon_explorer.run():
            return False
        
        return self.message.show_completion("시간의 균열 탈출 성공!", 50)
    
    def _run_skills_phase(self) -> bool:
        """스킬 튜토리얼 단계"""
        self.progress.phase = TutorialPhase.SKILLS
        
        dialogues = [
            ("karnos", "각 직업에는 고유한 스킬이 있다."),
            ("karnos", "전투 중 '스킬' 메뉴에서 사용할 수 있다."),
            ("karnos", "MP를 소모하니 신중하게 사용해라."),
            ("selena", "34개의 직업 중에서 4명을 선택해 파티를 구성해요."),
            ("selena", "한 번 선택하면 게임오버까지 변경할 수 없어요."),
            ("selena", "신중하게 골라주세요!")
        ]
        
        for speaker, text in dialogues:
            if not self.dialogue.show_dialogue(speaker, text):
                return False
        
        return self.message.show_completion("스킬 튜토리얼 완료!", 50)
    
    def _show_final_completion(self):
        """최종 완료 화면"""
        self.console.clear()
        
        title = "★ 튜토리얼 완료! ★"
        self.console.print(
            (self.console.width - len(title)) // 2,
            self.console.height // 2 - 6,
            title,
            fg=Colors.TITLE
        )
        
        lines = [
            "",
            "=== 획득 보상 ===",
            "",
            f"별의 파편: {self.progress.stellar_fragments}개",
            "해금 직업: 시간술사",
            "",
            "이제 던전 탐험을 시작하세요!",
            "",
            "[Z] 메인 메뉴로"
        ]
        
        y = self.console.height // 2 - 3
        for line in lines:
            color = Colors.NORMAL
            if "===" in line:
                color = Colors.WARNING
            elif "별의 파편" in line:
                color = Colors.TITLE
            elif "해금 직업" in line:
                color = Colors.OBJECTIVE
            
            self.console.print(
                (self.console.width - len(line)) // 2,
                y,
                line,
                fg=color
            )
            y += 1
        
        try:
            play_sfx("me", "Fanfare1")
        except:
            pass
        
        self.context.present(self.console)
        
        # 입력 대기
        time.sleep(0.1)
        for _ in tcod.event.get():
            pass
        
        while True:
            for event in tcod.event.wait():
                if isinstance(event, tcod.event.KeyDown):
                    if event.sym in (tcod.event.KeySym.RETURN, tcod.event.KeySym.z):
                        return
                elif isinstance(event, tcod.event.Quit):
                    return
    
    def _apply_rewards(self, result: Dict[str, Any]):
        """보상 적용"""
        try:
            from src.persistence.meta_progress import get_meta_progress, save_meta_progress
            meta = get_meta_progress()
            
            # 직업 해금
            if "time_mage" not in meta.unlocked_jobs:
                meta.unlocked_jobs.append("time_mage")
                logger.info("직업 해금: time_mage")
            
            # 별의 파편
            meta.star_fragments += result["rewards"]["stellar_fragments"]
            logger.info(f"별의 파편 +{result['rewards']['stellar_fragments']}")
            
            save_meta_progress()
        except Exception as e:
            logger.error(f"보상 적용 실패: {e}")


# =============================================================================
# 외부 호출 함수
# =============================================================================

def run_story_tutorial(console: tcod.console.Console, 
                       context: tcod.context.Context,
                       full_story: bool = True) -> Dict[str, Any]:
    """
    스토리 튜토리얼 실행 (외부 호출용)
    
    Args:
        full_story: True면 YAML 기반 풀 스토리 (22개 챕터)
                   False면 간략 버전
    """
    if full_story:
        runner = YAMLStoryRunner(console, context)
    else:
        runner = StoryTutorialRunner(console, context)
    return runner.run()


# 싱글톤
_story_runner: Optional[StoryTutorialRunner] = None

def get_story_runner() -> Optional[StoryTutorialRunner]:
    return _story_runner

def initialize_story_runner(console: tcod.console.Console, 
                            context: tcod.context.Context) -> StoryTutorialRunner:
    global _story_runner
    _story_runner = StoryTutorialRunner(console, context)
    return _story_runner


# =============================================================================
# YAML 기반 풀 스토리 러너 (22개 챕터 활용)
# =============================================================================

class YAMLStoryRunner:
    """
    YAML 기반 풀 스토리 튜토리얼
    
    data/tutorials/courses/ 의 22개 스토리 파일을 순서대로 실행
    각 챕터마다 대화 + 미니 던전/전투
    """
    
    def __init__(self, console: tcod.console.Console, context: tcod.context.Context):
        self.console = console
        self.context = context
        
        # 파티 (전사 시작)
        self.tutorial_char = Character("수련생", "warrior", level=1)
        self.party = [self.tutorial_char]
        self.inventory = Inventory(base_weight=100.0, party=self.party)
        
        # 서브 시스템
        self.dialogue = DialogueSystem(console, context)
        self.message = MessageRenderer(console, context)
        
        # 스토리 설정 로드
        self.config = load_story_config()
        self.chapters = self.config.get("story_chapters", [])
        self.npc_guides = self.config.get("npc_guides", {})
        
        # 진행 상태
        self.current_chapter = 0
        self.stellar_fragments = 0
    
    def run(self) -> Dict[str, Any]:
        """풀 스토리 실행"""
        result = {
            "completed": False,
            "job_unlocked": None,
            "rewards": {"stellar_fragments": 0}
        }
        
        logger.info("=== YAML 기반 풀 스토리 시작 ===")
        
        for chapter in self.chapters:
            chapter_id = chapter.get("id", "")
            chapter_title = chapter.get("title", "")
            tutorials = chapter.get("tutorials", [])
            
            logger.info(f"챕터 시작: {chapter_title}")
            
            # 챕터 타이틀
            if not self.message.show_title(chapter_title):
                return result
            
            # 각 튜토리얼 실행
            for tutorial_id in tutorials:
                if not self._run_tutorial(tutorial_id):
                    return result
                self.stellar_fragments += 10
            
            # 보스 챕터면 던전 탐험
            if chapter.get("boss_chapter"):
                if not self._run_boss_dungeon():
                    return result
                self.stellar_fragments += 50
        
        # 완료!
        result["completed"] = True
        result["job_unlocked"] = "time_mage"
        result["rewards"]["stellar_fragments"] = self.stellar_fragments
        
        self._show_completion()
        self._apply_rewards(result)
        
        safe_play_bgm("story")
        return result
    
    def _run_tutorial(self, tutorial_id: str) -> bool:
        """개별 튜토리얼 실행"""
        data = load_tutorial_yaml(tutorial_id)
        if not data:
            return True  # 파일 없으면 스킵
        
        title = data.get("title", "")
        
        # BGM 설정
        bgm = data.get("bgm", "")
        if bgm:
            bgm_key = bgm.replace(".ogg", "").replace("_", "")
            safe_play_bgm(bgm_key if bgm_key in BGM_MAP else "story")
        
        # 동적 변수 치환용 데이터
        job_id = self.tutorial_char.job_id if self.tutorial_char else "warrior"
        job_specific = data.get("job_specific_dialogue", {})
        job_data = job_specific.get(job_id, job_specific.get("default", {}))
        
        replacements = {
            "{job_intro}": job_data.get("intro", "이 직업만의 특별한 능력이 있어요!"),
            "{job_explanation}": job_data.get("explanation", "전투 중에 직접 체험해보세요!"),
        }
        
        # 메시지 표시
        messages = data.get("messages", [])
        for msg in messages:
            text = msg.get("text", "")
            if text:
                # 변수 치환
                for key, val in replacements.items():
                    text = text.replace(key, val)
                color = tuple(msg.get("color", [255, 255, 255]))
                self._show_message(text, color)
        
        # NPC 대화 (설명 먼저!)
        npc_dialogues = data.get("npc_dialogue", [])
        for dlg in npc_dialogues:
            npc = dlg.get("npc", "")
            text = dlg.get("text", "")
            if npc and text:
                # 변수 치환
                for key, val in replacements.items():
                    text = text.replace(key, val)
                if not self.dialogue.show_dialogue(npc, text):
                    return False
        
        # 전투/플레이 섹션은 대화 후에 실행!
        combat_data = data.get("combat_tutorial", {})
        playable = data.get("playable", {})
        
        if playable.get("enabled"):
            playable_type = playable.get("type", "")
            if playable_type == "combat":
                if not self._run_combat_section(combat_data or {"spawn_enemy": {"hp": 30, "brv": 50}}):
                    return False
            elif playable_type == "dungeon":
                if not self._run_mini_dungeon():
                    return False
        elif combat_data.get("enabled"):
            if not self._run_combat_section(combat_data):
                return False
        
        return True
    
    def _run_combat_section(self, combat_data: Dict) -> bool:
        """전투 섹션 실행"""
        from src.ui.combat_ui import run_combat
        
        safe_play_bgm("battle")
        
        # 적 생성
        spawn = combat_data.get("spawn_enemy", {})
        enemy_name = spawn.get("name", "시간 왜곡체")
        enemy_hp = spawn.get("hp", 50)
        enemy_brv = spawn.get("brv", 100)
        
        template = EnemyTemplate(
            enemy_id="story_enemy",
            name=enemy_name,
            level=1,
            hp=enemy_hp,
            mp=10,
            physical_attack=5,
            physical_defense=2,
            magic_attack=5,
            magic_defense=2,
            speed=40,
            max_brv=enemy_brv,
            init_brv=enemy_brv,  # 시작 BRV = max (BREAK 연습용)
            luck=5,
            accuracy=70,
            evasion=3
        )
        enemy = SimpleEnemy(template, level_modifier=1.0)
        
        result, _ = run_combat(
            self.console, self.context,
            self.party, [enemy], self.inventory
        )
        
        # 패배해도 부활
        for char in self.party:
            char.current_hp = char.max_hp
            char.current_mp = char.max_mp
        
        safe_play_bgm("story")
        return True
    
    def _run_mini_dungeon(self) -> bool:
        """미니 던전 실행"""
        dungeon_explorer = StoryDungeonExplorer(
            self.console, self.context, self.party, self.inventory
        )
        return dungeon_explorer.run()
    
    def _run_boss_dungeon(self) -> bool:
        """보스 던전 실행"""
        self.dialogue.show_dialogue("selena", "시간 포식자의 둥지에요...")
        self.dialogue.show_dialogue("karnos", "각오해라. 쉽지 않을 것이다.")
        
        # 미니 던전
        if not self._run_mini_dungeon():
            return False
        
        # 보스전
        self.message.show_objective("⚔ 시간 포식자 출현!")
        safe_play_bgm("boss")
        
        template = EnemyTemplate(
            enemy_id="time_devourer",
            name="시간 포식자",
            level=1,
            hp=150,
            mp=30,
            physical_attack=8,
            physical_defense=5,
            magic_attack=10,
            magic_defense=5,
            speed=50,
            max_brv=200,
            init_brv=100,
            luck=10,
            accuracy=80,
            evasion=10
        )
        boss = SimpleEnemy(template, level_modifier=1.0)
        
        from src.ui.combat_ui import run_combat
        result, _ = run_combat(
            self.console, self.context,
            self.party, [boss], self.inventory
        )
        
        # 패배해도 부활하고 재도전
        while result != CombatState.VICTORY:
            for char in self.party:
                char.current_hp = char.max_hp
                char.current_mp = char.max_mp
            self.dialogue.show_dialogue("selena", "괜찮아요! 다시 도전해봐요!")
            
            boss = SimpleEnemy(template, level_modifier=1.0)
            result, _ = run_combat(
                self.console, self.context,
                self.party, [boss], self.inventory
            )
        
        self.dialogue.show_dialogue("selena", "해냈어요! 시공 균열이 닫히고 있어요!")
        return True
    
    def _show_message(self, text: str, color: Tuple[int, int, int]):
        """메시지 표시"""
        self.console.clear()
        self.console.print(
            (self.console.width - len(text)) // 2,
            self.console.height // 2,
            text,
            fg=color
        )
        self.context.present(self.console)
        time.sleep(1.5)
    
    def _show_completion(self):
        """완료 화면"""
        self.message.show_completion(
            f"★ 스토리 튜토리얼 완료! ★",
            self.stellar_fragments
        )
    
    def _apply_rewards(self, result: Dict[str, Any]):
        """보상 적용"""
        try:
            from src.persistence.meta_progress import get_meta_progress, save_meta_progress
            meta = get_meta_progress()
            
            if "time_mage" not in meta.unlocked_jobs:
                meta.unlocked_jobs.append("time_mage")
            
            meta.star_fragments += result["rewards"]["stellar_fragments"]
            save_meta_progress()
        except Exception as e:
            logger.error(f"보상 적용 실패: {e}")


# 하위 호환성을 위한 별칭
StoryTutorialPlayer = StoryTutorialRunner
DialogueRunner = DialogueSystem
TutorialCombatRunner = CombatTutorial
TutorialState = TutorialPhase
