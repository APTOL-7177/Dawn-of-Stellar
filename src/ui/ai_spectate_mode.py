"""
AI 관전 모드 - AI가 자동으로 게임을 플레이하는 것을 관전

Features:
- AI 파티 자동 구성
- AI 전투 자동 진행
- AI 탐험 자동 진행
- AI 판단 해설 실시간 표시
- 실제 게임 화면과 연동
- 실제 키보드 입력 시뮬레이션 (pyautogui)
"""

import tcod.console
import tcod.event
import time
from typing import Optional, List, Dict, Any, Callable
from dataclasses import dataclass, field

from src.core.logger import get_logger
from src.ui.tcod_display import Colors
from src.ui.input_handler import GameAction, unified_input_handler
from src.ui import gathering_ui

# 실제 키보드 입력 시뮬레이션
try:
    import pyautogui
    pyautogui.FAILSAFE = False  # 마우스 코너 이동시 중단 방지
    pyautogui.PAUSE = 0.02  # 키 입력 간격
    KEYBOARD_SIMULATION_AVAILABLE = True
except ImportError:
    KEYBOARD_SIMULATION_AVAILABLE = False

logger = get_logger("ai_spectate")

# 실제 키보드 입력 사용 여부
USE_REAL_KEYBOARD = True  # True: 실제 키 입력, False: 내부 GameAction 반환

# GameAction → 실제 키 매핑
ACTION_TO_KEY = {
    GameAction.MOVE_UP: 'up',
    GameAction.MOVE_DOWN: 'down',
    GameAction.MOVE_LEFT: 'left',
    GameAction.MOVE_RIGHT: 'right',
    GameAction.CONFIRM: 'z',  # Z키 = 확인
    GameAction.CANCEL: 'x',   # X키 = 취소
    GameAction.MENU: 'escape',
    GameAction.OPEN_INVENTORY: 'i',
    GameAction.OPEN_CHARACTER: 'c',
    GameAction.WAIT: 'space',
    GameAction.ESCAPE: 'escape',
}

def send_real_key(action: GameAction) -> bool:
    """
    실제 키보드 입력을 시뮬레이션
    
    Args:
        action: GameAction enum
        
    Returns:
        True if key was sent, False otherwise
    """
    if not USE_REAL_KEYBOARD or not KEYBOARD_SIMULATION_AVAILABLE:
        return False
    
    key = ACTION_TO_KEY.get(action)
    if key:
        try:
            pyautogui.press(key)
            logger.debug(f"[KEYBOARD] 키 입력: {key} ({action.name})")
            return True
        except Exception as e:
            logger.error(f"[KEYBOARD] 키 입력 실패: {e}")
            return False
    return False

def ai_press_key(action: GameAction) -> Optional[GameAction]:
    """
    AI가 키를 입력합니다.
    USE_REAL_KEYBOARD가 True면 실제 키를 누르고 None 반환
    False면 GameAction을 반환 (기존 방식)
    """
    if USE_REAL_KEYBOARD and KEYBOARD_SIMULATION_AVAILABLE:
        send_real_key(action)
        time.sleep(0.05)  # 키 입력 후 약간의 딜레이
        return None  # 실제 키 입력했으므로 None 반환
    else:
        return action  # 기존 방식: GameAction 반환


# 콘솔 화면 텍스트 추출
def extract_console_text(console: tcod.console.Console) -> str:
    """
    tcod 콘솔의 내용을 텍스트로 추출
    
    실제 플레이어가 "보는" 화면과 동일한 정보를 LLM에게 제공
    """
    if console is None:
        return ""
    
    try:
        width = console.width
        height = console.height
        
        lines = []
        for y in range(height):
            line = ""
            for x in range(width):
                try:
                    ch = console.ch[x, y]
                    if ch == 0 or ch == 32:  # 빈 공간
                        line += " "
                    else:
                        line += chr(ch) if ch < 65536 else "?"
                except (IndexError, ValueError):
                    line += " "
            # 오른쪽 공백 제거
            lines.append(line.rstrip())
        
        # 위아래 빈 줄 제거
        while lines and not lines[0].strip():
            lines.pop(0)
        while lines and not lines[-1].strip():
            lines.pop()
        
        return "\n".join(lines)
    except Exception as e:
        logger.warning(f"콘솔 텍스트 추출 실패: {e}")
        return ""


def extract_console_with_colors(console: tcod.console.Console) -> str:
    """
    콘솔 내용 + 색상 힌트 추출 (중요한 요소 강조)
    
    색상으로 중요 정보 표시:
    - 빨강: 적, 위험
    - 초록: 아이템, 안전
    - 노랑: 중요 오브젝트
    - 흰색: 플레이어
    """
    if console is None:
        return ""
    
    try:
        width = console.width
        height = console.height
        
        lines = []
        for y in range(height):
            line = ""
            for x in range(width):
                try:
                    ch = console.ch[x, y]
                    fg = console.fg[x, y]  # (R, G, B)
                    
                    if ch == 0 or ch == 32:
                        line += " "
                    else:
                        char = chr(ch) if ch < 65536 else "?"
                        # 색상으로 중요도 표시 (간단한 마커)
                        r, g, b = fg[0], fg[1], fg[2]
                        if r > 200 and g < 100:  # 빨강 계열 - 적/위험
                            char = f"[!{char}]"
                        elif g > 200 and r < 100:  # 초록 계열 - 아이템
                            char = f"[+{char}]"
                        elif r > 200 and g > 200:  # 노랑 계열 - 중요
                            char = f"[*{char}]"
                        line += char
                except (IndexError, ValueError):
                    line += " "
            lines.append(line.rstrip())
        
        while lines and not lines[0].strip():
            lines.pop(0)
        while lines and not lines[-1].strip():
            lines.pop()
        
        return "\n".join(lines)
    except Exception as e:
        logger.warning(f"콘솔 색상 텍스트 추출 실패: {e}")
        return ""


# 현재 콘솔 참조 (화면 텍스트 추출용)
_current_console: Optional[tcod.console.Console] = None

def set_current_console(console: tcod.console.Console):
    """현재 콘솔 설정 (화면 텍스트 추출용)"""
    global _current_console
    _current_console = console

def get_screen_text() -> str:
    """현재 화면의 텍스트 내용 반환"""
    if _current_console:
        return extract_console_text(_current_console)
    return ""


# AI 해설을 저장할 전역 변수 (게임 UI에서 접근)
_ai_commentary: List[str] = []
_ai_current_action: str = ""
_ai_mode_enabled: bool = False

# 버그 헌터 로그
_bug_reports: List[Dict] = []
_action_history: List[str] = []

# AI 전투 결정 캐시 (상태별 메뉴 네비게이션용)
_current_combat_action = None  # 현재 LLM이 결정한 BotAction
_combat_action_step = 0  # 현재 진행 단계 (0: 결정받음, 1: 스킬선택, 2: 대상선택)


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
    set_current_console(console)  # 화면 텍스트 추출용 콘솔 설정
    gathering_ui.set_ai_spectate_mode(True)  # 채집 UI 자동 진행 활성화
    
    # 봇 클라이언트용 상태 내보내기 활성화
    try:
        from src.bot import enable_export
        enable_export(True)
        logger.info("봇 상태 내보내기 활성화")
    except ImportError:
        pass
    
    add_ai_commentary("🤖 AI 관전 모드 시작!")
    
    # AutoPlayAI 인스턴스 생성 - 즉시 LLM 연동 테스트
    ai = None
    use_llm = True

    try:
        from src.multiplayer.llm_player_bot import create_auto_play_ai, PlayStyle
        ai = create_auto_play_ai(model="gpt-oss:20b", style=PlayStyle.BALANCED)
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

    # 채집 상태 추적 (5번 입력 필요)
    pending_harvest = {'location': None, 'counter': 0}  # 위치와 누적 입력 횟수

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
    
    # AI 탐험 상태 (LLM 호출 최소화)
    _ai_exploration_state = {
        'target': None,  # 현재 목표 좌표
        'target_type': None,  # 목표 유형 (stairs, explore, enemy, item)
        'step_count': 0,  # 이동 스텝 카운터
        'last_llm_call': 0,  # 마지막 LLM 호출 스텝
        'llm_interval': 50,  # LLM 재호출 간격 (50스텝 = 더 적은 호출)
        'last_enemy_count': 0,  # 마지막으로 감지한 적 수
        'last_item_count': 0,  # 마지막으로 감지한 아이템 수
        'destroy_item_index': None,  # 파괴할 아이템 인덱스
        'explored_count': 0,  # 탐험한 타일 수
        'last_position': None,  # 마지막 위치 (왔다갔다 감지용)
        'oscillation_count': 0,  # 왔다갔다 카운터
    }
    
    def is_cooking_pot_at(dungeon, x, y) -> bool:
        """해당 위치에 요리솥이 있는지 확인"""
        from src.gathering.harvestable import HarvestableType
        if hasattr(dungeon, 'harvestables'):
            for h in dungeon.harvestables:
                if h.x == x and h.y == y and h.object_type == HarvestableType.COOKING_POT:
                    return True
        return False
    
    def get_safe_move(dungeon, px, py, dx, dy, reason: str = "") -> GameAction:
        """이동 가능한 방향으로만 이동 (벽/요리솥 충돌 방지) + 이유 로깅"""
        import random
        
        # 원하는 방향 먼저 시도
        nx, ny = px + dx, py + dy
        tile = dungeon.get_tile(nx, ny)
        
        # 요리솥은 그냥 통과 (AI 모드에서는 요리 UI 자동 열기 비활성화됨)
        
        if tile and tile.walkable:
            direction_name = ""
            if dy < 0:
                direction_name = "↑"
                action = GameAction.MOVE_UP
            elif dy > 0:
                direction_name = "↓"
                action = GameAction.MOVE_DOWN
            elif dx < 0:
                direction_name = "←"
                action = GameAction.MOVE_LEFT
            elif dx > 0:
                direction_name = "→"
                action = GameAction.MOVE_RIGHT
            else:
                return ai_press_key(GameAction.WAIT)
            
            if reason:
                log_action(f"{direction_name} {reason}")
            return ai_press_key(action)
        
        # 원하는 방향이 막혀있으면 다른 방향 시도
        directions = [
            (GameAction.MOVE_UP, 0, -1, "↑"),
            (GameAction.MOVE_DOWN, 0, 1, "↓"),
            (GameAction.MOVE_LEFT, -1, 0, "←"),
            (GameAction.MOVE_RIGHT, 1, 0, "→"),
        ]
        random.shuffle(directions)
        
        for action, adx, ady, dir_name in directions:
            nx, ny = px + adx, py + ady
            tile = dungeon.get_tile(nx, ny)
            if tile and tile.walkable:
                log_action(f"{dir_name} 우회 (원래 방향 막힘)")
                return ai_press_key(action)
        
        log_action("⏸️ 대기 (모든 방향 막힘)")
        return ai_press_key(GameAction.WAIT)
    
    def find_item_to_destroy(inv) -> int:
        """무게 초과 시 파괴할 아이템 찾기 (불필요한 무거운 아이템 우선)"""
        if not inv or not hasattr(inv, 'slots') or not inv.slots:
            return -1
        
        # 아이템 점수 계산 (낮을수록 파괴 우선순위 높음)
        # 점수 = (희귀도 * 10) - (무게 * 5) + (유용성)
        # 유용성: 회복=5, 장비=10, 요리=-2, 재료=-5
        
        from src.equipment.item_system import ItemType, ItemRarity
        
        candidates = []
        for i, slot in enumerate(inv.slots):
            item = slot.item
            
            # 장비된 아이템은 제외
            if hasattr(item, 'is_equipped') and item.is_equipped:
                continue
            
            # 점수 계산
            score = 0
            
            # 희귀도 점수 (높을수록 보존)
            rarity = getattr(item, 'rarity', ItemRarity.COMMON)
            rarity_score = {
                ItemRarity.COMMON: 0,
                ItemRarity.UNCOMMON: 2,
                ItemRarity.RARE: 5,
                ItemRarity.EPIC: 10,
                ItemRarity.LEGENDARY: 20,
            }.get(rarity, 0)
            score += rarity_score
            
            # 무게 점수 (무거울수록 파괴 우선)
            weight = getattr(item, 'weight', 0.5)
            score -= weight * 3
            
            # 유형별 점수
            item_type = getattr(item, 'item_type', None)
            if item_type == ItemType.WEAPON or item_type == ItemType.ARMOR or item_type == ItemType.ACCESSORY:
                score += 15  # 장비는 보존
            elif item_type == ItemType.CONSUMABLE:
                # 회복 아이템은 보존
                if hasattr(item, 'heal_amount') and item.heal_amount > 0:
                    score += 8
                else:
                    score += 2
            elif item_type == ItemType.MATERIAL:
                score -= 2  # 재료는 파괴 우선
            elif item_type == ItemType.COOKING:
                score += 5  # 요리는 어느정도 보존
            else:
                score -= 3  # 기타 아이템은 파괴 우선
            
            candidates.append((i, score, weight, item.name if hasattr(item, 'name') else 'unknown'))
        
        if not candidates:
            return -1
        
        # 점수 낮은 순 (파괴 우선순위 높은 순)으로 정렬
        candidates.sort(key=lambda x: (x[1], -x[2]))  # 점수 낮고 무게 무거운 순
        
        best = candidates[0]
        logger.info(f"[AI] 파괴 대상: {best[3]} (점수={best[1]:.1f}, 무게={best[2]:.1f}kg)")
        return best[0]
    
    # AI 탐험 입력 제공 콜백
    def ai_exploration_input(exploration_sys, party, inv) -> GameAction:
        """AI가 탐험 입력 결정 - A* 경로 우선, LLM은 목표만 결정"""
        nonlocal floor_number, dungeon, exploration, current_path
        import traceback
        import random

        # exploration_sys의 던전 사용 (최신 맵)
        current_dungeon = exploration_sys.dungeon if hasattr(exploration_sys, 'dungeon') else dungeon

        # 봇 클라이언트용 상태 내보내기
        try:
            from src.bot import export_exploration_state
            screen_text = get_screen_text()
            export_exploration_state(exploration_sys, party, current_dungeon, screen_text)
        except ImportError:
            pass

        try:
            # ===== 인벤토리 무게 초과 체크 (최우선) =====
            if inv and hasattr(inv, 'current_weight') and hasattr(inv, 'max_weight'):
                if inv.current_weight > inv.max_weight:
                    # 무게 초과! 아이템 파괴 필요
                    destroy_idx = _ai_exploration_state.get('destroy_item_index')
                    
                    if destroy_idx is None:
                        # 파괴할 아이템 찾기
                        destroy_idx = find_item_to_destroy(inv)
                        if destroy_idx >= 0:
                            _ai_exploration_state['destroy_item_index'] = destroy_idx
                            item_name = inv.slots[destroy_idx].item.name if destroy_idx < len(inv.slots) else 'unknown'
                            log_action(f"⚠️ 무게 초과! {inv.current_weight:.1f}/{inv.max_weight:.1f}kg")
                            log_action(f"🗑️ 파괴 대상: {item_name}")
                            add_ai_commentary(f"🗑️ 무게 초과 - {item_name} 파괴")
                    
                    if destroy_idx is not None and destroy_idx >= 0:
                        # 인벤토리 열기 또는 아이템 파괴 진행
                        # 인벤토리 UI가 열려있으면 해당 아이템 선택 후 V 키
                        # 여기서는 인벤토리 열기 먼저
                        
                        # 파괴 완료 확인 (무게가 줄었으면)
                        if inv.current_weight <= inv.max_weight:
                            log_action("✅ 무게 정상화")
                            _ai_exploration_state['destroy_item_index'] = None
                        else:
                            # 아이템 직접 제거 (UI 없이)
                            try:
                                removed = inv.remove_item(destroy_idx, 1)
                                if removed:
                                    log_action(f"🗑️ {removed.name} 파괴 완료")
                                    add_ai_commentary(f"🗑️ {removed.name} 버림")
                                _ai_exploration_state['destroy_item_index'] = None
                                # 다음 프레임에서 다시 무게 체크
                                return ai_press_key(GameAction.WAIT)
                            except Exception as e:
                                logger.warning(f"아이템 파괴 실패: {e}")
                                _ai_exploration_state['destroy_item_index'] = None

            # 현재 위치 확인
            current_pos = (exploration_sys.player.x, exploration_sys.player.y)
            _ai_exploration_state['step_count'] += 1

            # 막힌 상태 감지
            if last_position[0] == current_pos:
                stuck_counter[0] += 1
                if stuck_counter[0] > 10:
                    log_bug("StuckInPlace", f"같은 위치에 갇힘: {current_pos}",
                           game_state={"position": current_pos, "floor": floor_number})
                    stuck_counter[0] = 0
                    current_path.clear()  # 경로 초기화
                    _ai_exploration_state['target'] = None
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
            
            # ===== 계단 위에 있으면 바로 진입 =====
            if stairs_pos and (px, py) == stairs_pos:
                log_action("🚪 계단 위! 진입")
                add_ai_commentary("⬇️ 다음 층으로!")
                return ai_press_key(GameAction.CONFIRM)

            # ===== 채집 상태 체크 (5번 입력 필요) =====
            current_pos = (px, py)

            # 같은 위치에서 채집 중이면 카운터 증가
            if pending_harvest['location'] == current_pos:
                pending_harvest['counter'] += 1
                remaining = 5 - pending_harvest['counter']

                if remaining > 0:
                    log_action(f"🌿 채집 진행 중 ({pending_harvest['counter']}/5)")
                    return ai_press_key(GameAction.CONFIRM)
                else:
                    # 5번 완료 - 채집 완료
                    log_action("🌿 채집 완료!")
                    pending_harvest['location'] = None
                    pending_harvest['counter'] = 0
                    return ai_press_key(GameAction.CONFIRM)

            # 현재 위치에 채집 오브젝트가 있으면 (요리솥 제외)
            if hasattr(current_dungeon, 'harvestables'):
                from src.gathering.harvestable import HarvestableType
                for harvestable in current_dungeon.harvestables:
                    # 요리솥은 채집 대상이 아님
                    if harvestable.object_type == HarvestableType.COOKING_POT:
                        continue
                    if harvestable.x == px and harvestable.y == py:
                        if hasattr(harvestable, 'can_harvest') and harvestable.can_harvest(None):
                            # 새로운 채집 시작
                            if pending_harvest['location'] != current_pos:
                                log_action(f"🌿 채집 시작: {harvestable.object_type.value}")
                                pending_harvest['location'] = current_pos
                                pending_harvest['counter'] = 1  # 첫 번째 입력
                                add_ai_commentary(f"🌿 {harvestable.object_type.value} 채집! (1/5)")
                                return ai_press_key(GameAction.CONFIRM)

            # 채집 상태 아니면 초기화
            if pending_harvest['location']:
                pending_harvest['location'] = None
                pending_harvest['counter'] = 0

            # ===== 마을 활동 (LLM 기반) =====
            if is_town and ai and use_llm:
                from src.multiplayer.llm_player_bot import TownState, TownAction
                
                # 마을 상태 수집
                shop_items = []
                if hasattr(exploration_sys, 'shop') and exploration_sys.shop:
                    for item in getattr(exploration_sys.shop, 'items', [])[:5]:
                        shop_items.append({
                            'name': getattr(item, 'name', 'unknown'),
                            'price': getattr(item, 'price', 0)
                        })
                
                # 인벤토리 아이템
                inv_items = []
                if inv and hasattr(inv, 'slots'):
                    for slot in inv.slots[:5]:
                        item = getattr(slot, 'item', None)
                        if item:
                            inv_items.append({
                                'name': getattr(item, 'name', 'unknown'),
                                'count': getattr(slot, 'quantity', 1)
                            })
                
                town_state = TownState(
                    party_hp_percent=party_hp,
                    party_mp_percent=party_mp,
                    gold=getattr(inv, 'gold', 0) if inv else 0,
                    inventory_items=inv_items,
                    shop_items=shop_items,
                    inventory_weight=getattr(inv, 'current_weight', 0) if inv else 0,
                    max_weight=getattr(inv, 'max_weight', 20) if inv else 20
                )
                
                # LLM 마을 결정
                try:
                    town_action = ai.decide_town_action(town_state)
                    log_action(f"🏘️ 마을 LLM: {town_action.action_type} - {town_action.reasoning}")
                    add_ai_commentary(f"🏘️ {town_action.reasoning[:30]}")
                    
                    # 마을 행동 처리
                    if town_action.action_type == "depart":
                        # 던전 출발 - 계단으로 이동
                        if stairs_pos:
                            sx, sy = stairs_pos
                            dist_to_stairs = abs(sx - px) + abs(sy - py)
                            if dist_to_stairs == 0:
                                log_action("🚪 마을: 던전 입장!")
                                return ai_press_key(GameAction.CONFIRM)
                            else:
                                dx = 1 if sx > px else (-1 if sx < px else 0)
                                dy = 1 if sy > py else (-1 if sy < py else 0)
                                return get_safe_move(current_dungeon, px, py, dx, dy, "상점으로")
                    elif town_action.action_type == "rest":
                        # 휴식 - 여관 찾기 (임시: CONFIRM)
                        log_action("🛏️ 휴식 중...")
                        return ai_press_key(GameAction.CONFIRM)
                    elif town_action.action_type == "buy":
                        # 구매 - 상점 찾기 (임시: CONFIRM)
                        log_action(f"🛒 구매: {town_action.target}")
                        return ai_press_key(GameAction.CONFIRM)
                    else:
                        # 기타 행동 - 계단으로 이동
                        if stairs_pos:
                            sx, sy = stairs_pos
                            dx = 1 if sx > px else (-1 if sx < px else 0)
                            dy = 1 if sy > py else (-1 if sy < py else 0)
                            return get_safe_move(current_dungeon, px, py, dx, dy, "마을 이동")
                except Exception as e:
                    log_bug("TownLLMError", str(e))
            
            # 마을 폴백: 계단으로 이동
            elif is_town and stairs_pos:
                sx, sy = stairs_pos
                dist_to_stairs = abs(sx - px) + abs(sy - py)
                if dist_to_stairs == 0:
                    return ai_press_key(GameAction.CONFIRM)
                dx = 1 if sx > px else (-1 if sx < px else 0)
                dy = 1 if sy > py else (-1 if sy < py else 0)
                return get_safe_move(current_dungeon, px, py, dx, dy, "마을→계단")

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
                    _ai_exploration_state['target'] = enemy_pos
                    _ai_exploration_state['target_type'] = 'enemy'
                    log_action(f"👾 적 발견! {closest_enemy.name} 추적 ({len(path)}스텝)")
                    add_ai_commentary(f"👾 {closest_enemy.name} 발견! 전투 준비!")

            # ===== 왔다갔다 감지 =====
            last_pos = _ai_exploration_state.get('last_position')
            if last_pos and last_pos == (px, py):
                _ai_exploration_state['oscillation_count'] += 1
                if _ai_exploration_state['oscillation_count'] > 5:
                    # 왔다갔다 감지! 경로 초기화하고 새 목표 강제 설정
                    log_action("⚠️ 왔다갔다 감지 - 새 목표 설정")
                    current_path.clear()
                    _ai_exploration_state['target'] = None
                    _ai_exploration_state['oscillation_count'] = 0
            else:
                _ai_exploration_state['oscillation_count'] = 0
            _ai_exploration_state['last_position'] = (px, py)

            # ===== 경로 따라가기 (A* 우선) =====
            if current_path:
                next_pos = current_path[0]
                dx = next_pos[0] - px
                dy = next_pos[1] - py

                tile = current_dungeon.get_tile(next_pos[0], next_pos[1])
                
                # 문 처리 (잠긴 문 또는 일반 문)
                if tile:
                    from src.world.tile import TileType
                    
                    # 잠긴 문 - 상호작용으로 열기 시도
                    if tile.tile_type == TileType.LOCKED_DOOR:
                        key_id = getattr(tile, 'key_id', None)
                        log_action(f"🚪 잠긴 문 발견 (키: {key_id})")
                        add_ai_commentary(f"🚪 문이 잠겨있다...")
                        
                        # 열쇠 확인
                        if hasattr(exploration_sys, 'player') and hasattr(exploration_sys.player, 'keys'):
                            if key_id and key_id in exploration_sys.player.keys:
                                log_action(f"🔑 열쇠 사용: {key_id}")
                                add_ai_commentary(f"🔑 열쇠로 문 열기!")
                                return ai_press_key(GameAction.CONFIRM)  # 문 열기 시도
                        
                        # 열쇠 없으면 경로 재계산
                        log_action("🔒 열쇠 없음 - 다른 길 탐색")
                        current_path.clear()
                        _ai_exploration_state['target'] = None
                        return ai_press_key(GameAction.WAIT)
                    
                    # 일반 문 - 그냥 지나감 (walkable)
                    elif tile.tile_type == TileType.DOOR:
                        log_action("🚪 문 통과")
                
                if tile and tile.walkable:
                    current_path.pop(0)
                    
                    # 경로 완료 시
                    if not current_path:
                        log_action("✅ 경로 완료")
                        target_type = _ai_exploration_state.get('target_type', 'unknown')
                        _ai_exploration_state['target'] = None
                        
                        # 계단 위에 도착했으면 바로 진입
                        if target_type == 'stairs' and stairs_pos and (px + dx, py + dy) == stairs_pos:
                            log_action("🚪 계단 도착! 진입")
                            add_ai_commentary("⬇️ 다음 층으로!")
                            # 이동 후 CONFIRM
                    
                    # 안전한 이동 (벽 충돌 방지)
                    target_type = _ai_exploration_state.get('target_type', 'unknown')
                    reason = f"경로 이동 ({target_type})"
                    return get_safe_move(current_dungeon, px, py, dx, dy, reason)
                else:
                    # 경로가 막힘 - 문인지 확인
                    if tile:
                        from src.world.tile import TileType
                        if tile.tile_type in [TileType.DOOR, TileType.LOCKED_DOOR, TileType.SECRET_DOOR]:
                            log_action("🚪 문 앞에서 대기 - 상호작용 시도")
                            return ai_press_key(GameAction.CONFIRM)
                    
                    # 일반 막힘 - 경로 재계산
                    log_action("🚧 경로 막힘 - 재계산")
                    current_path.clear()
                    _ai_exploration_state['target'] = None

            # ===== LLM 호출 조건 체크 (엄격하게) =====
            # LLM은 규칙 기반으로 해결 안 될 때만 호출
            need_llm_call = False
            call_reason = ""
            
            # 규칙 기반으로 먼저 목표 설정 시도
            if not current_path and not _ai_exploration_state['target']:
                # 1순위: 계단이 발견되었으면 계단으로 (탐험 30타일 이상)
                if stairs_pos and len(explored_tiles) > 30:
                    _ai_exploration_state['target'] = stairs_pos
                    _ai_exploration_state['target_type'] = 'stairs'
                    path = astar_pathfind(current_dungeon, (px, py), stairs_pos)
                    if path:
                        current_path.extend(path)
                        log_action(f"🎯 규칙: 계단으로 ({len(path)}스텝)")
                        add_ai_commentary(f"⬇️ 계단으로 이동!")
                
                # 2순위: 미탐험 영역 찾기 (A* 경로 존재하는 곳만)
                if not current_path:
                    unexplored_targets = []
                    
                    # 더 넓은 범위에서 검색
                    for dx_s in range(-25, 26):
                        for dy_s in range(-25, 26):
                            nx, ny = px + dx_s, py + dy_s
                            if (nx, ny) not in explored_tiles:
                                tile = current_dungeon.get_tile(nx, ny)
                                if tile and tile.walkable:
                                    dist = abs(dx_s) + abs(dy_s)
                                    if dist > 2:  # 너무 가까운 곳 제외
                                        unexplored_targets.append(((nx, ny), dist))
                    
                    # 경로가 있는 타겟만 선택
                    if unexplored_targets:
                        unexplored_targets.sort(key=lambda x: x[1])  # 가까운 순
                        
                        for target, dist in unexplored_targets[:10]:  # 가까운 10개만 시도
                            path = astar_pathfind(current_dungeon, (px, py), target)
                            if path:
                                _ai_exploration_state['target'] = target
                                _ai_exploration_state['target_type'] = 'explore'
                                current_path.extend(path)
                                log_action(f"🎯 규칙: 탐험 {target} ({len(path)}스텝)")
                                break
                    
                    # 미탐험 영역 없거나 경로 없으면 → 출구 찾기
                    if not current_path:
                        log_action("🔍 출구 탐색 중...")
                        
                        # 문이나 복도 찾기 (현재 방에서 나가기)
                        from src.world.tile import TileType
                        exit_targets = []
                        
                        for dx_s in range(-20, 21):
                            for dy_s in range(-20, 21):
                                nx, ny = px + dx_s, py + dy_s
                                tile = current_dungeon.get_tile(nx, ny)
                                if tile:
                                    # 문, 복도 (탐험하지 않은 인접 타일이 있는 곳)
                                    is_exit = False
                                    if tile.tile_type in [TileType.DOOR, TileType.FLOOR]:
                                        # 주변에 미탐험 타일이 있는지 확인
                                        for ddx, ddy in [(-1,0),(1,0),(0,-1),(0,1)]:
                                            adj_tile = current_dungeon.get_tile(nx+ddx, ny+ddy)
                                            if adj_tile and adj_tile.walkable and (nx+ddx, ny+ddy) not in explored_tiles:
                                                is_exit = True
                                                break
                                    
                                    if is_exit and (nx, ny) != (px, py):
                                        dist = abs(dx_s) + abs(dy_s)
                                        exit_targets.append(((nx, ny), dist))
                        
                        if exit_targets:
                            exit_targets.sort(key=lambda x: x[1])
                            for target, dist in exit_targets[:5]:
                                path = astar_pathfind(current_dungeon, (px, py), target)
                                if path:
                                    _ai_exploration_state['target'] = target
                                    _ai_exploration_state['target_type'] = 'exit'
                                    current_path.extend(path)
                                    log_action(f"🚪 출구 발견! {target} ({len(path)}스텝)")
                                    add_ai_commentary(f"🚪 출구로 이동!")
                                    break
                
                # 규칙으로 해결 안 되면 LLM 호출
                if not current_path:
                    need_llm_call = True
                    call_reason = "규칙 실패 - LLM 필요"
            
            # 주기적 재평가는 삭제 (왔다갔다 원인)
            # HP 위험할 때만 LLM 호출
            if party_hp < 25 and _ai_exploration_state['step_count'] - _ai_exploration_state['last_llm_call'] >= 30:
                need_llm_call = True
                call_reason = f"HP 위험 ({party_hp:.0f}%)"
            
            _ai_exploration_state['last_enemy_count'] = len(nearby_enemies_list)

            # LLM 호출 (목표만 결정)
            if need_llm_call and ai and use_llm and not is_town and not using_enemy_path:
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

                # 채집 오브젝트 (요리솥 제외)
                if hasattr(current_dungeon, 'harvestables'):
                    from src.gathering.harvestable import HarvestableType
                    for harvestable in current_dungeon.harvestables:
                        if harvestable.object_type == HarvestableType.COOKING_POT:
                            continue
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
                
                # ===== 환경 타일 정보 수집 (LLM 인식용) =====
                hazard_tiles = []
                safe_tiles = []
                objects = []
                
                # 시야 내 환경 타일 분석
                for tile_info in visible_tiles:
                    tx, ty = tile_info.get('x', 0), tile_info.get('y', 0)
                    tile = current_dungeon.get_tile(tx, ty)
                    if tile:
                        # 위험 타일 (용암, 독가스, 함정 등)
                        if hasattr(tile, 'damage') and tile.damage > 0:
                            hazard_tiles.append({
                                'pos': (tx, ty),
                                'type': getattr(tile, 'tile_type', 'hazard'),
                                'damage': tile.damage
                            })
                        elif hasattr(tile, 'is_hazard') and tile.is_hazard:
                            hazard_tiles.append({
                                'pos': (tx, ty),
                                'type': getattr(tile, 'hazard_type', 'unknown'),
                                'damage': getattr(tile, 'damage', 5)
                            })
                        # 안전 타일
                        elif tile_info.get('walkable', False):
                            safe_tiles.append((tx, ty))
                        
                        # 오브젝트 (보물상자, NPC 등)
                        if tile_info.get('type') == 'chest':
                            objects.append({'pos': (tx, ty), 'type': 'chest', 'interactable': True})
                
                # 채집 오브젝트도 objects에 추가 (요리솥 제외)
                if hasattr(current_dungeon, 'harvestables'):
                    from src.gathering.harvestable import HarvestableType
                    for harvestable in current_dungeon.harvestables:
                        if harvestable.object_type == HarvestableType.COOKING_POT:
                            continue
                        is_visible = False
                        if hasattr(exploration_sys, 'fov_map') and exploration_sys.fov_map:
                            is_visible = exploration_sys.fov_map.visible[harvestable.x, harvestable.y]
                        if is_visible and hasattr(harvestable, 'can_harvest') and harvestable.can_harvest(None):
                            objects.append({
                                'pos': (harvestable.x, harvestable.y),
                                'type': harvestable.object_type.value if hasattr(harvestable.object_type, 'value') else 'harvestable',
                                'interactable': True
                            })
                
                # ===== 회복 아이템 정보 수집 =====
                healing_items = []
                current_gold = 0
                if inv:
                    current_gold = getattr(inv, 'gold', 0)
                    for slot in getattr(inv, 'slots', []):
                        item = getattr(slot, 'item', None)
                        if item and hasattr(item, 'heal_amount') and item.heal_amount > 0:
                            healing_items.append({
                                'name': item.name,
                                'heal': item.heal_amount,
                                'count': getattr(slot, 'quantity', 1)
                            })
                        elif item and hasattr(item, 'item_type') and 'potion' in str(item.item_type).lower():
                            healing_items.append({
                                'name': item.name,
                                'heal': getattr(item, 'heal_amount', 50),
                                'count': getattr(slot, 'quantity', 1)
                            })

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
                    unexplored_directions=unexplored_directions if unexplored_directions else [(0, -1), (0, 1), (-1, 0), (1, 0)],
                    # 새로운 필드들
                    hazard_tiles=hazard_tiles[:10],  # 위험 타일 (최대 10개)
                    safe_tiles=safe_tiles[:20],  # 안전 타일 (최대 20개)
                    objects=objects[:10],  # 오브젝트 (최대 10개)
                    healing_items=healing_items[:5],  # 회복 아이템 (최대 5개)
                    gold=current_gold  # 현재 골드
                )

                # LLM 목표 결정 (A* 경로 생성)
                try:
                    log_action(f"🤖 LLM 호출: {call_reason} - 위치({px}, {py})")
                    logger.info(f"[AI] 🤖 LLM 호출 ({call_reason})")
                    
                    _ai_exploration_state['last_llm_call'] = _ai_exploration_state['step_count']

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

                    # 현재 위치 채집 확인 (요리솥 제외)
                    if hasattr(current_dungeon, 'harvestables'):
                        from src.gathering.harvestable import HarvestableType
                        for harvestable in current_dungeon.harvestables:
                            if harvestable.object_type == HarvestableType.COOKING_POT:
                                continue
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
                            return ai_press_key(GameAction.CONFIRM)

                        if has_item_here:
                            log_action("📦 LLM 결정: 아이템 줍기")
                            add_ai_commentary("🎁 아이템 획득!")
                            return ai_press_key(GameAction.CONFIRM)

                        if has_harvest_here:
                            log_action("🌿 LLM 결정: 채집")
                            add_ai_commentary("🌿 채집!")
                            return ai_press_key(GameAction.CONFIRM)

                    # ===== 계단이 근처이고 LLM이 특정 결정 못 했으면 자동 진입 =====
                    if has_stairs_here and action.action_type in ["rest", "interact"]:
                        log_action("🚪 자동: 계단 진입")
                        add_ai_commentary("⬇️ 계단으로!")
                        return ai_press_key(GameAction.CONFIRM)

                    # ===== LLM 이동 결정 =====
                    if action.action_type == "move" and action.direction and action.direction != (0, 0):
                        dx, dy = action.direction
                        return get_safe_move(current_dungeon, px, py, dx, dy, "LLM 이동")

                    elif action.action_type == "move" and action.target_position:
                        tx, ty = action.target_position
                        _ai_exploration_state['target'] = (tx, ty)
                        log_action(f"🎯 LLM 목표: ({tx}, {ty})")
                        add_ai_commentary(f"🎯 목표: ({tx}, {ty})")
                        
                        # A* 경로 생성
                        path = astar_pathfind(current_dungeon, (px, py), action.target_position)
                        if path:
                            current_path.clear()
                            current_path.extend(path)
                            log_action(f"🛤️ A* 경로: {len(path)}스텝")
                            
                            # 첫 번째 이동 즉시 실행
                            if current_path:
                                next_pos = current_path[0]
                                dx = next_pos[0] - px
                                dy = next_pos[1] - py
                                current_path.pop(0)
                                return get_safe_move(current_dungeon, px, py, dx, dy, "LLM 경로")
                        else:
                            # 경로 없으면 목표 방향으로 직접 이동
                            dx = 1 if tx > px else (-1 if tx < px else 0)
                            dy = 1 if ty > py else (-1 if ty < py else 0)
                            return get_safe_move(current_dungeon, px, py, dx, dy, "LLM 목표 방향")

                    elif action.action_type == "fight":
                        log_action("⚔️ LLM 전투 결정")
                        # 가장 가까운 적으로
                        if exploration_sys.enemies:
                            closest = min(exploration_sys.enemies,
                                key=lambda e: abs(e.x - px) + abs(e.y - py))
                            dx = 1 if closest.x > px else (-1 if closest.x < px else 0)
                            dy = 1 if closest.y > py else (-1 if closest.y < py else 0)
                            return get_safe_move(current_dungeon, px, py, dx, dy, f"적 추적 ({closest.name})")

                except Exception as e:
                    log_bug("LLMExplorationError", str(e))
                    log_action(f"❌ LLM 실패: {str(e)[:50]}")
                    add_ai_commentary(f"🔧 LLM 에러 - 규칙 기반으로 전환")
                    _ai_exploration_state['target'] = None

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
                    return ai_press_key(GameAction.CONFIRM)  # 일단 CONFIRM으로 전투 유도

            # ===== 폴백: 탐험 (경로 없을 때) =====
            import random
            
            # 현재 상태 로그
            log_action(f"🔍 탐험 중 (탐험 {len(explored_tiles)}타일)")
            add_ai_commentary(f"🔍 새로운 길 탐색 중...")
            
            directions = [
                (GameAction.MOVE_UP, 0, -1, "↑"),
                (GameAction.MOVE_DOWN, 0, 1, "↓"),
                (GameAction.MOVE_LEFT, -1, 0, "←"),
                (GameAction.MOVE_RIGHT, 1, 0, "→"),
            ]
            
            # 이동 가능한 방향 찾기 (미방문 우선)
            possible_moves = []
            unexplored_moves = []
            for game_action, dx, dy, dir_name in directions:
                nx, ny = px + dx, py + dy
                tile = current_dungeon.get_tile(nx, ny)
                if tile and tile.walkable:
                    possible_moves.append((game_action, dir_name))
                    if (nx, ny) not in explored_tiles:
                        unexplored_moves.append((game_action, dir_name))
            
            if unexplored_moves:
                # 미방문 방향 우선
                chosen, dir_name = random.choice(unexplored_moves)
                log_action(f"{dir_name} 미탐험 지역으로")
                return ai_press_key(chosen)
            elif possible_moves:
                # 탐험한 지역이지만 이동 가능
                chosen, dir_name = random.choice(possible_moves)
                log_action(f"{dir_name} 이동 (새 경로 탐색)")
                return ai_press_key(chosen)
            
            # 정말 막힘 - WAIT
            log_action("⏸️ 대기 (막다른 곳)")
            add_ai_commentary("⏸️ 막다른 곳...")
            return ai_press_key(GameAction.WAIT)
        
        except Exception as e:
            log_bug("ExplorationAIError", str(e), traceback.format_exc())
            import random
            return ai_press_key(random.choice([GameAction.MOVE_UP, GameAction.MOVE_DOWN, GameAction.MOVE_LEFT, GameAction.MOVE_RIGHT]))
    
    # AI 전투: LLM 결정 + UI 실행
    _ai_combat_state = {'char': None, 'step': 0, 'last_action_time': 0, 'llm_action': None, 'target_name': None}
    _combat_bots = {}  # 캐릭터별 봇 캐시
    
    def ai_combat_input(ui, combat_manager, current_char, inv) -> GameAction:
        """AI 전투 - LLM이 행동 결정 → UI 통해 실행"""
        import time
        from src.ui.combat_ui import CombatUIState
        from src.combat.combat_manager import ActionType
        
        state = ui.state
        now = time.time()
        
        # 너무 빠른 입력 방지 (0.05초 간격)
        time_since_last = now - _ai_combat_state['last_action_time']
        if time_since_last < 0.05:
            return None
        _ai_combat_state['last_action_time'] = now
        
        logger.info(f"[COMBAT] 상태: {state.value}, 캐릭터: {current_char.name}, LLM: {_ai_combat_state.get('llm_action')}")
        
        # 봇 클라이언트용 상태 내보내기
        try:
            from src.bot import export_combat_state
            screen_text = get_screen_text()
            ui_state_str = state.value if hasattr(state, 'value') else str(state)
            # party 추출 시도 (ATB에서)
            party = getattr(combat_manager, 'allies', None)
            if not party and hasattr(combat_manager, 'atb'):
                party = [c for c in combat_manager.atb.get_action_order() if hasattr(c, 'job_id')]
            export_combat_state(combat_manager, current_char, screen_text, ui_state_str, party)
        except ImportError:
            pass
        
        # 캐릭터 바뀌면 LLM 호출
        if _ai_combat_state['char'] != current_char.name:
            _ai_combat_state['char'] = current_char.name
            _ai_combat_state['step'] = 0
            _ai_combat_state['llm_action'] = None
            _ai_combat_state['target_name'] = None
            
            # LLM 전투 결정
            try:
                from src.multiplayer.llm_player_bot import create_llm_bot, get_bot_action_for_combat
                
                char_name = current_char.name
                if char_name not in _combat_bots:
                    job = getattr(current_char, 'job_id', 'warrior')
                    _combat_bots[char_name] = create_llm_bot(char_name, job, "gpt-oss:20b")
                
                bot = _combat_bots[char_name]
                
                # 화면 텍스트 추출 (실제 플레이어가 보는 화면)
                screen_text = get_screen_text()
                action = get_bot_action_for_combat(bot, combat_manager, current_char, inv, screen_text=screen_text)
                
                _ai_combat_state['llm_action'] = action.action_type
                _ai_combat_state['target_name'] = action.target_name
                _ai_combat_state['skill_id'] = getattr(action, 'skill_id', None)
                
                logger.info(f"[COMBAT] 🤖 LLM 결정: {current_char.name} → {action.action_type.value}, 타겟: {action.target_name}")
                log_action(f"🤖 {current_char.name}: {action.action_type.value}")
                add_ai_commentary(f"🤖 {action.reasoning[:30] if action.reasoning else '전투 행동'}...")
                
            except Exception as e:
                logger.error(f"[COMBAT] LLM 실패: {e}")
                _ai_combat_state['llm_action'] = ActionType.BRV_ATTACK  # 폴백
                _ai_combat_state['target_name'] = None
        
        _ai_combat_state['step'] += 1
        
        # 무한 루프 방지
        if _ai_combat_state['step'] > 50:
            logger.warning(f"[COMBAT] ⚠️ 강제 진행")
            _ai_combat_state['step'] = 0
            return ai_press_key(GameAction.CONFIRM)
        
        llm_action = _ai_combat_state.get('llm_action', ActionType.BRV_ATTACK)
        
        # 상태별 처리
        logger.info(f"[COMBAT] 상태: {state}, LLM 행동: {llm_action}")
        
        if state == CombatUIState.ACTION_MENU:
            if not ui.action_menu or not ui.action_menu.items:
                logger.warning(f"[COMBAT] 메뉴 없음!")
                return None
            
            # LLM 행동에 맞는 메뉴 찾기 (item.value로 ActionType 비교)
            target_menu = None
            brv_menu = None  # BRV 공격 메뉴 (인덱스 0)
            hp_menu = None   # HP 공격 메뉴 (인덱스 1)
            skill_menu = None
            item_menu = None
            defend_menu = None
            
            # 메뉴 목록 로그
            menu_texts = [(i, item.text, item.enabled) for i, item in enumerate(ui.action_menu.items)]
            logger.info(f"[COMBAT] 메뉴 목록: {menu_texts}")
            
            for i, item in enumerate(ui.action_menu.items):
                if not item.enabled:
                    continue
                
                text = item.text
                
                # 텍스트로 메뉴 타입 판단 (다양한 변형 처리)
                if '스킬' in text or 'skill' in text.lower() or text == '기술':
                    skill_menu = i
                elif '아이템' in text or 'item' in text.lower() or '소모품' in text:
                    item_menu = i
                elif '방어' in text or 'defend' in text.lower() or '가드' in text:
                    defend_menu = i
                elif '도망' in text or '도주' in text or 'flee' in text.lower():
                    pass  # 무시
                elif '기믹' in text or '상세' in text:
                    pass  # 무시
                # 첫 두 메뉴는 BRV/HP 공격 (활성화된 것만)
                elif brv_menu is None:
                    brv_menu = i  # 첫 번째 비-기능 메뉴 = BRV
                elif hp_menu is None:
                    hp_menu = i  # 두 번째 = HP
            
            # LLM 결정 값 추출
            llm_action_value = llm_action.value if hasattr(llm_action, 'value') else str(llm_action)
            logger.debug(f"[COMBAT] llm_action_value='{llm_action_value}'")
            
            # LLM 결정에 맞는 메뉴 선택
            if llm_action_value in ['brv_attack', 'BRV_ATTACK']:
                target_menu = brv_menu
            elif llm_action_value in ['hp_attack', 'HP_ATTACK']:
                target_menu = hp_menu
            elif llm_action_value in ['skill', 'SKILL']:
                target_menu = skill_menu
            elif llm_action_value in ['item', 'ITEM']:
                target_menu = item_menu
            elif llm_action_value in ['defend', 'DEFEND']:
                target_menu = defend_menu
            
            # 못 찾으면 첫 번째 활성화 메뉴
            if target_menu is None:
                logger.warning(f"[COMBAT] LLM 메뉴 못 찾음: {llm_action}, 폴백 실행")
                for i, item in enumerate(ui.action_menu.items):
                    if item.enabled:
                        target_menu = i
                        logger.info(f"[COMBAT] 폴백 메뉴: {i} = {item.text}")
                        break
            
            logger.info(f"[COMBAT] 메뉴 매칭: LLM={llm_action}, brv={brv_menu}, hp={hp_menu}, skill={skill_menu} → target={target_menu}")
            
            if target_menu is not None:
                cur = ui.action_menu.cursor_index
                if cur < target_menu:
                    return ai_press_key(GameAction.MOVE_DOWN)
                elif cur > target_menu:
                    return ai_press_key(GameAction.MOVE_UP)
                else:
                    log_action(f"⚔️ {current_char.name}: {ui.action_menu.items[cur].text}")
                    _ai_combat_state['step'] = 0
                    return ai_press_key(GameAction.CONFIRM)
            
            return None
        
        elif state == CombatUIState.TARGET_SELECT:
            targets = getattr(ui, 'current_target_list', [])
            target_name = _ai_combat_state.get('target_name')
            
            # 타겟 선택 우선순위
            target_idx = None
            
            # 1. LLM이 지정한 이름으로 찾기 (정확히 일치)
            if target_name and target_name not in ['enemy', 'ally', 'self']:
                for i, t in enumerate(targets):
                    if getattr(t, 'name', '') == target_name:
                        target_idx = i
                        break
            
            # 2. 못 찾으면 전략적 선택 (적 타겟인 경우)
            if target_idx is None and targets:
                llm_action = _ai_combat_state.get('llm_action')
                
                # 적 공격인 경우 - HP 낮은 적 우선 (막타용)
                enemies_in_targets = [t for t in targets if hasattr(t, 'is_alive') and t in getattr(combat_manager, 'enemies', [])]
                if enemies_in_targets:
                    # HP 비율이 가장 낮은 적
                    best = None
                    best_hp_pct = 999
                    for i, t in enumerate(targets):
                        if t in enemies_in_targets:
                            hp = getattr(t, 'current_hp', 1)
                            max_hp = getattr(t, 'max_hp', 1)
                            hp_pct = hp / max_hp * 100
                            if hp_pct < best_hp_pct:
                                best_hp_pct = hp_pct
                                best = i
                    if best is not None:
                        target_idx = best
            
            # 3. 그래도 없으면 첫 번째
            if target_idx is None:
                target_idx = 0
            
            # 커서 이동
            cur = getattr(ui, 'target_cursor', 0)
            if cur < target_idx:
                return ai_press_key(GameAction.MOVE_DOWN)
            elif cur > target_idx:
                return ai_press_key(GameAction.MOVE_UP)
            
            # 선택
            if targets:
                target = targets[target_idx] if target_idx < len(targets) else targets[0]
                log_action(f"🎯 → {getattr(target, 'name', '?')}")
            _ai_combat_state['step'] = 0
            return ai_press_key(GameAction.CONFIRM)
        
        elif state == CombatUIState.SKILL_MENU:
            if not ui.skill_menu or not ui.skill_menu.items:
                return ai_press_key(GameAction.CANCEL)
            
            # LLM이 선택한 스킬 ID로 찾기
            llm_skill_id = _ai_combat_state.get('skill_id')
            target_skill = None
            
            for i, item in enumerate(ui.skill_menu.items):
                if not item.enabled:
                    continue
                
                # 스킬 ID나 이름으로 매칭
                skill = item.value
                skill_id = getattr(skill, 'id', getattr(skill, 'skill_id', '')) if skill else ''
                skill_name = getattr(skill, 'name', item.text) if skill else item.text
                
                if llm_skill_id and (skill_id == llm_skill_id or llm_skill_id in skill_name):
                    target_skill = i
                    break
            
            # LLM 스킬 못 찾으면 첫 번째 활성화 스킬
            if target_skill is None:
                for i, item in enumerate(ui.skill_menu.items):
                    if item.enabled and item.value is not None:  # 뒤로가기 제외
                        target_skill = i
                        break
            
            if target_skill is not None:
                cur = ui.skill_menu.cursor_index
                if cur < target_skill:
                    return ai_press_key(GameAction.MOVE_DOWN)
                elif cur > target_skill:
                    return ai_press_key(GameAction.MOVE_UP)
                else:
                    skill_name = ui.skill_menu.items[cur].text
                    log_action(f"✨ {skill_name}")
                    add_ai_commentary(f"✨ 스킬: {skill_name}")
                    _ai_combat_state['step'] = 0
                    return ai_press_key(GameAction.CONFIRM)
            
            return ai_press_key(GameAction.CANCEL)
        
        elif state == CombatUIState.ITEM_MENU:
            return ai_press_key(GameAction.CANCEL)
        
        elif state == CombatUIState.CARD_SELECT:
            # 마술사 카드 선택 UI - card_hand 리스트 사용
            card_hand = getattr(ui, 'card_hand', [])
            if card_hand:
                # 가장 높은 랭크의 카드 선택 (에이스 인 더 홀용)
                rank_order = ["A", "K", "Q", "J", "10", "9", "8", "7", "6", "5", "4", "3", "2"]
                best_idx = 0
                best_rank = 99
                for i, card in enumerate(card_hand):
                    rank = card.get('rank', '')
                    if card.get('is_joker'):
                        # 조커는 최고
                        best_idx = i
                        best_rank = -1
                        break
                    elif rank in rank_order:
                        r = rank_order.index(rank)
                        if r < best_rank:
                            best_rank = r
                            best_idx = i
                
                card_cursor = getattr(ui, 'card_cursor', 0)
                if card_cursor < best_idx:
                    return ai_press_key(GameAction.MOVE_RIGHT)
                elif card_cursor > best_idx:
                    return ai_press_key(GameAction.MOVE_LEFT)
                else:
                    selected_card = card_hand[best_idx]
                    card_name = f"{selected_card.get('suit', '?')}{selected_card.get('rank', '?')}"
                    log_action(f"🃏 카드: {card_name}")
                    add_ai_commentary(f"🃏 {card_name} 선택!")
                    _ai_combat_state['step'] = 0
                    return ai_press_key(GameAction.CONFIRM)
            # 카드 없으면 취소
            return ai_press_key(GameAction.CANCEL)
        
        elif state == CombatUIState.GIMMICK_VIEW:
            # 기믹 상세 보기 - 닫기
            return ai_press_key(GameAction.CANCEL)
        
        return None
    
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
    gathering_ui.set_ai_spectate_mode(False)  # 채집 UI 자동 진행 해제
    logger.info("AI 관전 모드 종료")

    return {"success": True, "stats": game_stats}
