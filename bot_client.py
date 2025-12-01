"""
Dawn of Stellar - 독립 봇 클라이언트

게임과 별도로 실행되며, 게임 상태를 읽고 키 입력으로 플레이

Usage:
    1. 게임 실행: python main.py
    2. 봇 활성화: user_data/enable_bot.txt 파일 생성 또는 BOT_EXPORT=1 환경변수
    3. 봇 클라이언트 실행: python bot_client.py
    
Features:
    - 게임 내부 상태 연동 (JSON 파일 공유)
    - 실제 키보드 입력 (Z=확인, X=취소)
    - LLM 기반 판단
"""

import os
import sys
import json
import time
from pathlib import Path
from typing import Optional, Dict, Any

# 프로젝트 루트 추가
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

# pyautogui
try:
    import pyautogui
    pyautogui.FAILSAFE = False
    pyautogui.PAUSE = 0.03
except ImportError:
    print("❌ pyautogui 필요: pip install pyautogui")
    sys.exit(1)


# 공유 상태 파일 경로
GAME_STATE_FILE = PROJECT_ROOT / "user_data" / "bot_state.json"
BOT_COMMAND_FILE = PROJECT_ROOT / "user_data" / "bot_command.json"
ENABLE_FILE = PROJECT_ROOT / "user_data" / "enable_bot.txt"


class BotClient:
    """독립 봇 클라이언트 - LLM 기반 자동 플레이"""
    
    # 게임 키 매핑 (Z=확인, X=취소)
    KEYS = {
        'up': 'up',
        'down': 'down', 
        'left': 'left',
        'right': 'right',
        'confirm': 'z',      # Z키 = 확인
        'cancel': 'x',       # X키 = 취소
        'enter': 'return',   # Enter
        'escape': 'escape',  # ESC
        'wait': 'space',
        'inventory': 'i',
        'character': 'c',
        'destroy': 'v',      # V키 = 아이템 파괴
        'z': 'z',
        'x': 'x',
        'v': 'v',
    }
    
    def __init__(self, model: str = "gpt-oss:20b", delay: float = 0.3):
        self.model = model
        self.delay = delay
        self.running = False
        self.last_state_time = 0
        
        # LLM 모듈 임포트
        self.llm_module = None
        self.combat_bots = {}  # 캐릭터별 봇 캐시
        self.exploration_ai = None
        
        # 탐험 상태 초기화
        self._goal = None
        self._goal_type = None
        self._goal_turns = 0
        self._path = []
        self._last_pos = None
        self._explored_map = {}
        self._position_history = []
        self._stuck_counter = 0
        self._failed_goals = set()
        self._move_count = 0
        self._current_floor = -1
        self._fast_mode = False
        
        self._init_llm()
    
    def _init_llm(self):
        """LLM 모듈 초기화"""
        try:
            from src.multiplayer import llm_player_bot
            self.llm_module = llm_player_bot
            
            # 탐험 AI 생성
            self.exploration_ai = llm_player_bot.create_auto_play_ai(
                model=self.model,
                style=llm_player_bot.PlayStyle.BALANCED
            )
            print(f"✅ LLM 모듈 로드: {self.model}")
        except Exception as e:
            print(f"❌ LLM 모듈 로드 실패: {e}")
            self.llm_module = None
    
    def _get_combat_bot(self, char_name: str, job: str = "warrior"):
        """캐릭터별 전투 봇 가져오기 (캐싱)"""
        if char_name not in self.combat_bots:
            if self.llm_module:
                self.combat_bots[char_name] = self.llm_module.create_llm_bot(
                    char_name, job, self.model, self.llm_module.PlayStyle.BALANCED
                )
        return self.combat_bots.get(char_name)
    
    def read_game_state(self, force: bool = False) -> Optional[Dict[str, Any]]:
        """게임 상태 파일 읽기 (쓰기 충돌 방지)"""
        try:
            if GAME_STATE_FILE.exists():
                mtime = GAME_STATE_FILE.stat().st_mtime
                # force=True면 항상 읽기, 아니면 갱신 체크
                if force or mtime > self.last_state_time:
                    self.last_state_time = mtime
                    # 파일 읽기 (여러 번 시도)
                    for _ in range(3):
                        try:
                            with open(GAME_STATE_FILE, 'r', encoding='utf-8') as f:
                                content = f.read()
                                if content.strip():
                                    return json.loads(content)
                        except json.JSONDecodeError:
                            time.sleep(0.02)  # 쓰기 완료 대기 (0.05→0.02)
                            continue
        except Exception as e:
            pass  # 조용히 실패
        return None
    
    def press_key(self, key_name: str):
        """실제 키 입력"""
        key = self.KEYS.get(key_name, key_name)
        try:
            pyautogui.press(key)
            print(f"⌨️ {key}")
        except Exception as e:
            print(f"❌ 키 입력 실패: {e}")
    
    def decide_action(self, state: Dict[str, Any]) -> str:
        """LLM으로 행동 결정"""
        mode = state.get('mode', 'unknown')
        
        # 파괴 모드 활성화 중이면 파괴 처리
        if hasattr(self, '_destroy_mode') and self._destroy_mode:
            return self._handle_destroy_item(state)
        
        # 인벤토리 모드 활성화 중이면 인벤토리 처리
        if hasattr(self, '_inventory_mode') and self._inventory_mode:
            return self._handle_inventory(state)
        
        if mode == 'combat':
            return self._decide_combat(state)
        elif mode == 'exploration':
            return self._decide_exploration(state)
        elif mode == 'menu':
            return self._decide_menu(state)
        elif mode == 'dialog' or mode == 'dialogue':
            # 대화창 - 자동 진행
            print("[대화] 자동 진행")
            return 'confirm'
        elif mode == 'result' or mode == 'victory':
            # 결과 화면 - 자동 진행
            print("[결과] 자동 진행")
            return 'confirm'
        else:
            return 'wait'
    
    def _decide_combat(self, state: Dict[str, Any]) -> str:
        """전투 행동 결정 - LLM 기반"""
        ui_state = state.get('ui_state', '').lower()
        current_actor = state.get('current_actor', '')
        enemies = state.get('enemies', [])
        
        print(f"[전투] UI: {ui_state}, 캐릭터: {current_actor}")
        
        # 전투 종료 (승리/패배) - 자동 진행
        if 'battle_end' in ui_state or 'end' in ui_state or 'result' in ui_state:
            print("  🏆 전투 종료! 자동 진행")
            return 'confirm'
        
        # UI 상태별 처리
        if 'waiting' in ui_state or 'executing' in ui_state:
            return None
        
        if 'target' in ui_state:
            # 타겟 선택 - LLM이 지정한 타겟 찾기
            return self._select_target(state)
        
        if 'skill' in ui_state:
            # 스킬 메뉴 - LLM이 지정한 스킬 선택
            return self._select_skill(state)
        
        if 'item' in ui_state:
            print("  → 아이템 취소")
            return 'cancel'
        
        if 'card' in ui_state:
            # 마술사 카드 선택 - 첫 번째 카드 선택
            # 카드 선택 상태 관리 (바로 confirm 안 보내도록)
            if not hasattr(self, '_card_wait'):
                self._card_wait = 2  # 2프레임 대기
            
            if self._card_wait > 0:
                self._card_wait -= 1
                print(f"  → 카드 선택 대기 ({self._card_wait})")
                return None  # 대기
            else:
                self._card_wait = 2  # 다음을 위해 리셋
                print("  → 카드 선택 (확정)")
                return 'confirm'
        
        if 'action' in ui_state:
            return self._decide_combat_action_llm(state)
        
        if current_actor:
            return 'confirm'
        
        return None
    
    def _select_target(self, state: Dict[str, Any]) -> str:
        """LLM이 지정한 타겟 선택"""
        enemies = state.get('enemies', [])
        alive_enemies = [e for e in enemies if e.get('is_alive', True)]
        
        # 새 타겟 선택 시작 (매번 LLM 타겟 가져오기)
        if not hasattr(self, '_target_selecting') or not self._target_selecting:
            self._target_selecting = True
            self._target_step = 0
            self._target_name = getattr(self, '_llm_target', None)
            self._target_idx = 0
            
            # 무효한 타겟 처리 ("none", None, 빈 문자열 등)
            invalid_targets = [None, '', 'none', 'null', '없음', 'target']
            if self._target_name and self._target_name.lower() not in invalid_targets:
                # 타겟 인덱스 찾기 (살아있는 적 기준)
                for i, e in enumerate(alive_enemies):
                    ename = e.get('name', '').lower()
                    tname = self._target_name.lower()
                    # 정확한 매칭 또는 부분 매칭
                    if tname in ename or ename in tname:
                        self._target_idx = i
                        print(f"  🎯 타겟 발견: {e.get('name')} (인덱스 {i})")
                        break
                else:
                    # 못 찾으면 가장 약한 적 선택
                    if alive_enemies:
                        weakest = min(range(len(alive_enemies)), 
                                     key=lambda i: alive_enemies[i].get('hp', 999999))
                        self._target_idx = weakest
                        print(f"  🎯 타겟 없음 → 가장 약한 적: {alive_enemies[weakest].get('name')} (인덱스 {weakest})")
            else:
                # 무효한 타겟 → 가장 약한 적 선택
                if alive_enemies:
                    weakest = min(range(len(alive_enemies)), 
                                 key=lambda i: alive_enemies[i].get('hp', 999999))
                    self._target_idx = weakest
                    print(f"  🎯 타겟 무효 → 가장 약한 적: {alive_enemies[weakest].get('name')} (인덱스 {weakest})")
        
        # 타겟까지 이동
        if self._target_step < self._target_idx:
            self._target_step += 1
            print(f"  → 타겟 이동 ({self._target_step}/{self._target_idx})")
            return 'down'
        
        # 타겟 도착 - 확인
        target_display = alive_enemies[self._target_idx].get('name') if alive_enemies and self._target_idx < len(alive_enemies) else '첫 번째'
        print(f"  → 타겟 확인: {target_display}")
        self._target_selecting = False
        self._target_step = 0
        self._llm_target = None  # 사용 완료
        return 'confirm'
    
    def _select_skill(self, state: Dict[str, Any]) -> str:
        """LLM이 지정한 스킬 선택"""
        skills = state.get('skills', [])
        
        # 새 스킬 선택 시작
        if not hasattr(self, '_skill_selecting') or not self._skill_selecting:
            self._skill_selecting = True
            self._skill_step = 0
            self._skill_name = getattr(self, '_llm_skill', None)
            self._skill_idx = 0
            
            # 스킬 인덱스 찾기
            if self._skill_name and skills:
                for i, s in enumerate(skills):
                    sname = s.get('name', '').lower()
                    sid = s.get('id', '').lower()
                    target = self._skill_name.lower()
                    if target in sname or target in sid or sname in target:
                        self._skill_idx = i
                        print(f"  📜 스킬 발견: {s.get('name')} (인덱스 {i})")
                        break
        
        # 스킬까지 이동
        if self._skill_step < self._skill_idx:
            self._skill_step += 1
            print(f"  → 스킬 이동 ({self._skill_step}/{self._skill_idx})")
            return 'down'
        
        # 스킬 도착 - 확인
        print(f"  → 스킬 선택: {self._skill_name or '첫 번째'}")
        self._skill_selecting = False
        self._skill_step = 0
        self._llm_skill = None
        return 'confirm'
    
    def _decide_combat_action_llm(self, state: Dict[str, Any]) -> str:
        """전투 액션 메뉴에서 LLM 행동 결정"""
        current_actor = state.get('current_actor', '')
        allies = state.get('allies', [])
        
        # current_actor가 없으면 첫 번째 살아있는 아군 사용
        if not current_actor and allies:
            for a in allies:
                if a.get('is_alive', True):
                    current_actor = a.get('name', '')
                    break
        
        print(f"  [디버그] current_actor={current_actor}, allies={len(allies)}, llm={self.llm_module is not None}")
        
        # LLM 모듈 사용
        if self.llm_module and current_actor:
            try:
                llm = self.llm_module
                
                # 캐릭터별 봇 가져오기
                actor_job = 'warrior'
                for a in state.get('allies', []):
                    if a.get('name') == current_actor:
                        actor_job = a.get('job', 'warrior')
                        break
                
                bot = self._get_combat_bot(current_actor, actor_job)
                if bot:
                    # CombatState 생성 (atb_percent 포함)
                    allies = [llm.CombatantState(
                        name=a.get('name', ''),
                        job=a.get('job', ''),
                        hp=a.get('hp', 0),
                        max_hp=a.get('max_hp', 100),
                        mp=a.get('mp', 0),
                        max_mp=a.get('max_mp', 100),
                        brv=a.get('brv', 0),
                        max_brv=a.get('max_brv', 100),  # 기본값 100
                        atb_percent=a.get('atb_percent', 100.0),
                        is_alive=a.get('is_alive', True),
                        is_broken=a.get('is_broken', False),
                        buffs=[], debuffs=[]
                    ) for a in state.get('allies', [])]
                    
                    enemies = [llm.CombatantState(
                        name=e.get('name', ''),
                        job='enemy',
                        hp=e.get('hp', 0),
                        max_hp=e.get('max_hp', 100),
                        mp=0, max_mp=100,
                        brv=e.get('brv', 0),
                        max_brv=e.get('max_brv', 100),  # 기본값 100
                        atb_percent=e.get('atb_percent', 100.0),
                        is_alive=e.get('is_alive', True),
                        is_broken=e.get('is_broken', False),
                        buffs=[], debuffs=[]
                    ) for e in state.get('enemies', [])]
                    
                    # 스킬 정보 변환
                    skills_data = state.get('skills', [])
                    available_skills = []
                    for s in skills_data:
                        skill_info = llm.SkillInfo(
                            id=s.get('id', ''),
                            name=s.get('name', ''),
                            mp_cost=s.get('mp_cost', 0),
                            skill_type=s.get('skill_type', 'attack'),
                            description=s.get('description', ''),
                            cooldown_remaining=0
                        )
                        available_skills.append(skill_info)
                    
                    combat_state = llm.CombatState(
                        turn_count=state.get('turn', 0),
                        current_actor=current_actor,
                        allies=allies,
                        enemies=enemies,
                        available_skills=available_skills,
                        available_items=[],
                        screen_text=state.get('screen_text', '')
                    )
                    
                    # LLM 결정
                    action = bot.decide_combat_action(combat_state)
                    action_type = action.action_type.value
                    
                    print(f"  🤖 LLM: {action_type} → {action.target_name}")
                    if action.reasoning:
                        print(f"     💭 {action.reasoning[:40]}...")
                    
                    # 타겟/스킬 이름 저장 (타겟 선택 시 사용)
                    self._llm_target = action.target_name
                    self._llm_skill = action.skill_id  # skill_name이 아니라 skill_id
                    
                    # 메뉴 스텝 관리
                    if not hasattr(self, '_llm_action'):
                        self._llm_action = None
                        self._menu_step = 0
                    
                    # 새 액션이면 초기화
                    if self._llm_action != action_type:
                        self._llm_action = action_type
                        self._menu_step = 0
                    
                    # 메뉴 이동 (BRV=0, HP=1, 스킬=2, 아이템=3, 방어=4)
                    menu_pos = {'brv_attack': 0, 'hp_attack': 1, 'skill': 2, 'item': 3, 'defend': 4}
                    target_pos = menu_pos.get(action_type, 0)
                    
                    if self._menu_step < target_pos:
                        self._menu_step += 1
                        print(f"  ↓ 메뉴 이동 ({self._menu_step}/{target_pos})")
                        return 'down'
                    else:
                        self._llm_action = None
                        self._menu_step = 0
                        print(f"  → {action_type} 선택")
                        return 'confirm'
                        
            except Exception as e:
                print(f"  ⚠️ LLM 오류: {e}")
        
        # 폴백: BRV 공격
        print("  → BRV 공격 (폴백)")
        return 'confirm'
    
    def _decide_exploration(self, state: Dict[str, Any]) -> str:
        """탐험 행동 결정 - LLM 목표 결정 + A* 경로 탐색"""
        player_pos = state.get('player_pos', [0, 0])
        if isinstance(player_pos, list) and len(player_pos) >= 2:
            px, py = player_pos[0], player_pos[1]
        else:
            px, py = 0, 0
        
        stairs = state.get('stairs_pos')
        enemies = state.get('nearby_enemies', [])
        walkable = state.get('walkable_dirs', [])
        healing_points = state.get('healing_points', [])
        items = state.get('items', [])
        interactables = state.get('interactables', [])
        
        # 계단 위치 파싱
        sx, sy = None, None
        if stairs:
            if isinstance(stairs, (list, tuple)) and len(stairs) >= 2:
                sx, sy = stairs[0], stairs[1]
        
        # 맵 기억 초기화
        current_floor = state.get('floor', 1)
        if not hasattr(self, '_explored_map'):
            self._explored_map = {}  # {(x,y): set of walkable directions}
            self._path = []
            self._last_pos = None
            self._last_move = None
            self._blocked_dirs = {}  # {(x,y): set of blocked directions}
            self._position_history = []  # 최근 위치 기록 (순환 감지용)
            self._stuck_counter = 0  # 교착상태 카운터
            self._failed_goals = set()  # 도달 실패한 목표들
            self._current_floor = current_floor
        
        # 층 변경 감지 - 모든 탐색 상태 초기화
        if not hasattr(self, '_current_floor') or self._current_floor != current_floor:
            print(f"🆕 새 층 진입! (floor {current_floor}) - 탐색 상태 초기화")
            self._explored_map = {}
            self._path = []
            self._last_pos = None
            self._last_move = None
            self._blocked_dirs = {}
            self._position_history = []
            self._stuck_counter = 0
            self._failed_goals = set()
            self._goal = None
            self._goal_type = None
            self._goal_turns = 0
            self._move_count = 0  # A* 이동 카운터
            self._current_floor = current_floor
        
        current_pos = (px, py)
        dir_delta = {'up': (0, -1), 'down': (0, 1), 'left': (-1, 0), 'right': (1, 0)}
        delta_dir = {(0, -1): 'up', (0, 1): 'down', (-1, 0): 'left', (1, 0): 'right'}
        
        # 위치 히스토리 업데이트 (최근 10개)
        self._position_history.append(current_pos)
        if len(self._position_history) > 10:
            self._position_history.pop(0)
        
        # 순환 감지: 최근 10칸 중 같은 위치가 3번 이상
        is_cycling = self._position_history.count(current_pos) >= 3
        
        # 벽 감지: 이동했는데 위치가 안 바뀌면 벽!
        if self._last_pos and self._last_move:
            if current_pos == self._last_pos:
                # 위치 안 바뀜 = 벽!
                if self._last_pos not in self._blocked_dirs:
                    self._blocked_dirs[self._last_pos] = set()
                self._blocked_dirs[self._last_pos].add(self._last_move)
                self._stuck_counter += 1
                print(f"  🧱 벽 감지! {self._last_move} 방향 막힘 (stuck: {self._stuck_counter})")
            else:
                self._stuck_counter = 0  # 이동 성공하면 리셋
        
        # 실제 이동 가능한 방향 = walkable - blocked
        blocked_here = self._blocked_dirs.get(current_pos, set())
        real_walkable = [d for d in walkable if d not in blocked_here]
        
        if not real_walkable and walkable:
            # 모든 방향 막힘 - blocked 초기화하고 stuck 증가
            print(f"[탐험] ({px}, {py}) | 모든 방향 막힘, blocked 기록 초기화")
            self._blocked_dirs[current_pos] = set()
            blocked_here = set()  # 출력용 변수도 초기화
            real_walkable = walkable
            self._stuck_counter += 2
        
        # 현재 위치의 실제 이동 가능 방향 기억
        self._explored_map[current_pos] = set(real_walkable)
        
        # 교착상태 심각 - 기록 리셋
        if self._stuck_counter >= 5 or is_cycling:
            print(f"  ⚠️ 교착상태 감지! (stuck={self._stuck_counter}, cycling={is_cycling})")
            if hasattr(self, '_goal') and self._goal:
                self._failed_goals.add(self._goal)
            self._goal = None
            self._path = []
            self._stuck_counter = 0
            self._position_history = [current_pos]
            # blocked_dirs도 현재 위치만 초기화
            self._blocked_dirs[current_pos] = set()
            blocked_here = set()
        
        print(f"[탐험] ({px}, {py}) | 게임제공: {walkable} | 실제이동가능: {real_walkable} (막힘기록: {list(blocked_here)})")
        
        # 무게 초과 시 아이템 파괴
        is_overweight = state.get('is_overweight', False)
        weight_pct = state.get('weight_pct', 0)
        destroyable_items = state.get('destroyable_items', [])
        
        if is_overweight and destroyable_items and not hasattr(self, '_destroy_mode'):
            print(f"  ⚖️ 무게 초과! ({weight_pct}%) 아이템 파괴 시작")
            self._destroy_mode = 'opening'
            self._destroy_target_idx = destroyable_items[0].get('index', 0)
            self._destroy_target_name = destroyable_items[0].get('name', '')
            return 'inventory'  # i 키로 인벤토리 열기
        
        # 파괴 모드 처리
        if hasattr(self, '_destroy_mode') and self._destroy_mode:
            return self._handle_destroy_item(state)
        
        # HP 낮으면 인벤토리에서 회복 아이템 사용
        avg_hp = state.get('avg_hp_pct', 100)
        healing_items = state.get('healing_items', [])
        
        if avg_hp < 50 and healing_items and not hasattr(self, '_inventory_mode'):
            print(f"  💊 HP 낮음 ({avg_hp:.0f}%)! 인벤토리 열기")
            self._inventory_mode = 'opening'
            self._inventory_target_item = healing_items[0]['name']
            return 'inventory'  # i 키
        
        # 인벤토리 모드 처리
        if hasattr(self, '_inventory_mode') and self._inventory_mode:
            return self._handle_inventory(state)
        
        # 계단 위에 있으면 진입
        if sx is not None and px == sx and py == sy:
            print("🚪 계단 진입!")
            return 'confirm'
        
        # LLM에게 목표 결정 요청
        if not hasattr(self, '_goal'):
            self._goal = None
            self._goal_type = None
            self._goal_turns = 0
            self._move_count = 0  # A* 이동 카운터
        
        # A* 경로가 있으면 LLM 호출 없이 계속 이동
        if self._path and len(self._path) > 0:
            # 위험 상황만 체크 (HP 낮거나 적 근접)
            party_hp = self._calc_party_hp(state)
            has_nearby_enemy = len(enemies) > 0
            is_danger = party_hp < 30 or (has_nearby_enemy and party_hp < 50)
            
            if is_danger:
                # 위험하면 경로 취소하고 LLM 호출
                print(f"  ⚠️ 위험 감지! (HP:{party_hp:.0f}%, 적:{len(enemies)}명) - 경로 취소")
                self._goal = None
                self._path = []
            else:
                # 안전하면 A* 경로 따라 계속 이동
                next_pos = self._path[0]
                dx = next_pos[0] - px
                dy = next_pos[1] - py
                direction = delta_dir.get((dx, dy))
                
                if direction and direction in real_walkable:
                    self._path.pop(0)
                    remaining = len(self._path)
                    print(f"  ⚡ {direction} ({remaining}칸 남음) → {self._goal_type}")
                    self._last_pos = current_pos
                    self._last_move = direction
                    self._fast_mode = True
                    return direction
                else:
                    # 경로 막힘 - 재계산
                    print(f"  ❌ 경로 막힘, 재계산")
                    self._path = []
        
        # 목표 없거나 목표 도착 시에만 LLM 호출 (경로 없어도 목표 있으면 계속 이동)
        self._goal_turns += 1
        goal_reached = self._goal and current_pos == self._goal
        goal_failed = self._goal and self._goal in self._failed_goals
        goal_timeout = self._goal_turns >= 30  # 30턴 동안 도착 못하면 재설정
        need_llm = (self._goal is None or 
                    goal_reached or 
                    goal_failed or
                    goal_timeout)  # 목표 있으면 경로 없어도 계속 이동
        
        # 디버그: LLM 호출 조건
        print(f"  [DEBUG] goal={self._goal}, turns={self._goal_turns}, need_llm={need_llm}, path={len(self._path) if self._path else 0}")
        
        if need_llm and self.exploration_ai and self.llm_module:
            try:
                llm = self.llm_module
                stairs_tuple = (sx, sy) if sx is not None else None
                party_hp = self._calc_party_hp(state)
                
                # 가장 가까운 힐링 포인트
                nearest_healing = None
                if healing_points:
                    healing_points.sort(key=lambda h: abs(h[0] - px) + abs(h[1] - py))
                    nearest_healing = tuple(healing_points[0])
                
                # 가장 가까운 아이템
                nearest_item = None
                if items:
                    items.sort(key=lambda i: i.get('distance', 999))
                    nearest_item = tuple(items[0]['pos'])
                
                exploration_state = llm.ExplorationState(
                    current_floor=state.get('floor', 1),
                    current_position=(px, py),
                    visible_tiles=list(self._explored_map.keys())[-20:],
                    discovered_rooms=len(self._explored_map),
                    total_rooms=100,
                    nearby_enemies=[e.get('name', 'enemy') for e in enemies],
                    nearby_items=[i.get('name', 'item') for i in items],
                    nearby_exits=[stairs_tuple] if stairs_tuple else [],
                    party_hp_percent=party_hp,
                    party_mp_percent=50,
                    has_healing_point=bool(healing_points),
                    floor_type='dungeon',
                    stairs_down_position=stairs_tuple,
                    screen_text=state.get('screen_text', '')
                )
                
                action = self.exploration_ai.decide_exploration_action(exploration_state)
                
                # 우선순위 결정
                # 1. 체력 30% 이하 + 힐링 포인트 있으면 힐링
                # 2. LLM 결정 따르기
                if party_hp < 30 and nearest_healing:
                    self._goal = nearest_healing
                    self._goal_type = '💚 힐링'
                    print(f"  ⚠️ 체력 위험! ({party_hp:.0f}%) → 힐링 포인트")
                elif action.action_type == 'heal' and nearest_healing:
                    self._goal = nearest_healing
                    self._goal_type = '💚 힐링'
                elif action.action_type == 'item' and nearest_item:
                    self._goal = nearest_item
                    self._goal_type = '📦 아이템'
                elif action.action_type == 'stairs' and stairs_tuple:
                    # 계단이 15칸 이내면 직접, 아니면 중간 목표
                    sx_t, sy_t = stairs_tuple
                    dist_to_stairs = abs(sx_t - px) + abs(sy_t - py)
                    if dist_to_stairs <= 15:
                        self._goal = stairs_tuple
                        self._goal_type = '🚪 계단'
                    else:
                        # 계단 방향으로 가장 가까운 탐색된 바닥 (5~15칸)
                        best = self._find_walkable_toward(px, py, sx_t, sy_t, 5, 15)
                        if best:
                            self._goal = best
                            self._goal_type = f'🚪 계단방향'
                        else:
                            self._goal = stairs_tuple
                            self._goal_type = '🚪 계단(원거리)'
                elif action.action_type == 'explore':
                    # 탐험 목표 설정 - 15블록 정도 떨어진 바닥 타일 선호
                    TARGET_DIST = 15
                    
                    # 탐색된 바닥 타일 중에서 목표 거리에 가까운 것 찾기
                    def find_floor_goal(target_x, target_y):
                        """목표 지점에 가장 가까운 탐색된 바닥 타일 찾기"""
                        if not self._explored_map:
                            return None
                        
                        best_pos = None
                        best_score = float('inf')
                        
                        for pos in self._explored_map.keys():
                            # 목표 지점과의 거리
                            dist_to_target = abs(pos[0] - target_x) + abs(pos[1] - target_y)
                            # 현재 위치와의 거리
                            dist_from_current = abs(pos[0] - px) + abs(pos[1] - py)
                            
                            # 너무 가깝거나 현재 위치는 제외
                            if dist_from_current < 5:
                                continue
                            
                            # 목표 거리(15)에 가까울수록 좋음
                            score = abs(dist_from_current - TARGET_DIST) + dist_to_target * 0.5
                            
                            if score < best_score:
                                best_score = score
                                best_pos = pos
                        
                        return best_pos
                    
                    # 계단이 있으면 계단 방향으로
                    if stairs_tuple:
                        sx_t, sy_t = stairs_tuple
                        dist_to_stairs = abs(sx_t - px) + abs(sy_t - py)
                        if dist_to_stairs > TARGET_DIST:
                            # 계단 방향으로 15블록 지점 근처의 바닥 타일
                            ratio = TARGET_DIST / dist_to_stairs
                            mid_x = int(px + (sx_t - px) * ratio)
                            mid_y = int(py + (sy_t - py) * ratio)
                            floor_goal = find_floor_goal(mid_x, mid_y)
                            if floor_goal:
                                self._goal = floor_goal
                                self._goal_type = f'🔍 탐험 (계단방향 바닥)'
                            else:
                                self._goal = stairs_tuple
                                self._goal_type = '🚪 계단'
                        else:
                            self._goal = stairs_tuple
                            self._goal_type = '🚪 계단'
                    else:
                        # 계단 없으면 탐색된 바닥 중 먼 곳
                        for d in walkable:
                            ddx, ddy = dir_delta[d]
                            target_x = px + ddx * TARGET_DIST
                            target_y = py + ddy * TARGET_DIST
                            floor_goal = find_floor_goal(target_x, target_y)
                            if floor_goal:
                                self._goal = floor_goal
                                self._goal_type = f'🔍 탐험 ({d} 바닥)'
                                break
                    
                    if not self._goal:
                        # 폴백: 가장 먼 탐색된 바닥 타일
                        if self._explored_map and len(self._explored_map) > 5:
                            farthest = max(self._explored_map.keys(), 
                                          key=lambda p: abs(p[0] - px) + abs(p[1] - py))
                            self._goal = farthest
                            self._goal_type = '🔍 탐험 (최원거리 바닥)'
                        elif stairs_tuple:
                            # 탐색 초기면 계단으로
                            self._goal = stairs_tuple
                            self._goal_type = '🚪 계단 (초기탐색)'
                        else:
                            # 계단도 없으면 이동 가능 방향으로 15칸
                            if walkable:
                                d = walkable[0]
                                ddx, ddy = dir_delta[d]
                                self._goal = (px + ddx * 15, py + ddy * 15)
                                self._goal_type = f'🔍 탐험 ({d} 15칸)'
                elif action.action_type == 'flee' and enemies:
                    # 적 피하기 - 적 반대 방향으로
                    enemy = enemies[0]
                    ex, ey = enemy['pos']
                    flee_x = px + (px - ex)
                    flee_y = py + (py - ey)
                    self._goal = (flee_x, flee_y)
                    self._goal_type = '🏃 도주'
                elif action.direction and action.direction != (0, 0):
                    dx, dy = action.direction
                    self._goal = (px + dx * 15, py + dy * 15)  # 15블록 이동
                    self._goal_type = '➡️ 이동'
                else:
                    # 기본: 아이템 > 계단 (15칸 이내 바닥 타일로 제한)
                    if nearest_item:
                        ix, iy = nearest_item
                        dist = abs(ix - px) + abs(iy - py)
                        if dist <= 15:
                            self._goal = nearest_item
                            self._goal_type = '📦 아이템'
                        else:
                            best = self._find_walkable_toward(px, py, ix, iy, 5, 15)
                            self._goal = best if best else nearest_item
                            self._goal_type = f'📦 아이템방향'
                    elif stairs_tuple:
                        sx_t, sy_t = stairs_tuple
                        dist = abs(sx_t - px) + abs(sy_t - py)
                        if dist <= 15:
                            self._goal = stairs_tuple
                            self._goal_type = '🚪 계단(기본)'
                        else:
                            best = self._find_walkable_toward(px, py, sx_t, sy_t, 5, 15)
                            self._goal = best if best else stairs_tuple
                            self._goal_type = f'🚪 계단방향(기본)'
                
                # 목표 미설정 시 기본 목표 강제 설정
                if not self._goal:
                    if stairs_tuple:
                        best = self._find_walkable_toward(px, py, stairs_tuple[0], stairs_tuple[1], 3, 15)
                        self._goal = best if best else stairs_tuple
                        self._goal_type = '🚪 계단(폴백)'
                    elif walkable:
                        # 아무 방향으로 10칸
                        d = walkable[0]
                        ddx, ddy = dir_delta[d]
                        self._goal = (px + ddx * 10, py + ddy * 10)
                        self._goal_type = f'➡️ {d}(폴백)'
                
                self._goal_turns = 0
                self._path = []
                print(f"  🤖 LLM 결정: {self._goal_type} → {self._goal}")
                
            except Exception as e:
                print(f"  ⚠️ LLM 오류: {e}")
                self._goal = (sx, sy) if sx is not None else None
                self._goal_type = '🚪 계단(오류)'
        
        # 목표까지 A* 경로 계산
        if self._goal and (not self._path or self._last_pos != current_pos):
            self._path = self._find_path(current_pos, self._goal, walkable)
            self._last_pos = current_pos
            if self._path:
                print(f"  📍 경로 계산: {len(self._path)}칸 ({self._goal_type})")
        
        # 경로 따라가기
        if self._path:
            next_pos = self._path[0]
            dx = next_pos[0] - px
            dy = next_pos[1] - py
            
            direction = delta_dir.get((dx, dy))
            if direction and direction in real_walkable:
                self._path.pop(0)
                print(f"  → {direction} ({len(self._path)}칸 남음) [A*]")
                self._last_pos = current_pos
                self._last_move = direction
                return direction
            else:
                print(f"  ⚠️ 경로 막힘 - 재계산")
                self._path = []
                # 즉시 경로 재계산
                if self._goal:
                    self._path = self._find_path(current_pos, self._goal, real_walkable)
                    if self._path:
                        next_pos = self._path[0]
                        dx = next_pos[0] - px
                        dy = next_pos[1] - py
                        direction = delta_dir.get((dx, dy))
                        if direction and direction in real_walkable:
                            self._path.pop(0)
                            print(f"  → {direction} ({len(self._path)}칸 남음) [재계산]")
                            self._last_pos = current_pos
                            self._last_move = direction
                            return direction
        
        # 경로 없으면 미탐색 방향 우선
        if not real_walkable:
            print("  ❌ 이동 불가")
            return 'wait'
        
        unexplored = [d for d in real_walkable if (px + dir_delta[d][0], py + dir_delta[d][1]) not in self._explored_map]
        if unexplored:
            # 목표 방향에 가까운 미탐색 방향 우선
            if self._goal:
                unexplored.sort(key=lambda d: abs((px + dir_delta[d][0]) - self._goal[0]) + abs((py + dir_delta[d][1]) - self._goal[1]))
            choice = unexplored[0]
            print(f"  🔍 미탐색: {choice}")
            self._last_pos = current_pos
            self._last_move = choice
            return choice
        
        # 모두 탐색됨 - real_walkable 중 목표에 가까운 방향
        if self._goal and real_walkable:
            walkable_sorted = sorted(real_walkable, key=lambda d: abs((px + dir_delta[d][0]) - self._goal[0]) + abs((py + dir_delta[d][1]) - self._goal[1]))
            choice = walkable_sorted[0]
            print(f"  🎯 {self._goal_type}: {choice}")
            self._last_pos = current_pos
            self._last_move = choice
            return choice
        
        # 랜덤 (real_walkable에서만)
        import random
        choice = random.choice(real_walkable)
        print(f"  🎲 랜덤: {choice}")
        
        # 이동 기록 (벽 감지용)
        self._last_pos = current_pos
        self._last_move = choice
        return choice
    
    def _find_path(self, start: tuple, goal: tuple, current_walkable: list) -> list:
        """A* 경로 탐색 (탐색된 맵 + blocked_dirs 반영)"""
        import heapq
        
        dir_delta = {'up': (0, -1), 'down': (0, 1), 'left': (-1, 0), 'right': (1, 0)}
        all_dirs = ['up', 'down', 'left', 'right']
        
        # 휴리스틱: 맨해튼 거리
        def h(pos):
            return abs(pos[0] - goal[0]) + abs(pos[1] - goal[1])
        
        # 특정 위치에서 실제 이동 가능한 방향
        def get_walkable(pos):
            if pos == start:
                base = set(current_walkable)
            elif pos in self._explored_map:
                base = self._explored_map[pos]
            else:
                # 미탐색 지역은 모든 방향 가능하다고 가정
                base = set(all_dirs)
            # blocked_dirs 제외
            blocked = self._blocked_dirs.get(pos, set())
            return base - blocked
        
        # 시작점
        open_set = [(h(start), 0, start, [])]  # (f, g, pos, path)
        closed_set = set()
        g_scores = {start: 0}
        max_iterations = 500  # 무한 루프 방지
        
        iterations = 0
        while open_set and iterations < max_iterations:
            iterations += 1
            f, g, pos, path = heapq.heappop(open_set)
            
            # 목표 도달 (또는 근접)
            if pos == goal:
                return path
            if h(pos) <= 1 and len(path) > 0:
                # 목표 인접 - 마지막 한 칸 추가
                for d in all_dirs:
                    dx, dy = dir_delta[d]
                    if (pos[0] + dx, pos[1] + dy) == goal:
                        return path + [goal]
            
            if pos in closed_set:
                continue
            closed_set.add(pos)
            
            # 이웃 탐색
            walkable_dirs = get_walkable(pos)
            
            for d in walkable_dirs:
                dx, dy = dir_delta[d]
                next_pos = (pos[0] + dx, pos[1] + dy)
                
                if next_pos in closed_set:
                    continue
                
                new_g = g + 1
                
                # 더 좋은 경로가 이미 있으면 스킵
                if next_pos in g_scores and g_scores[next_pos] <= new_g:
                    continue
                
                g_scores[next_pos] = new_g
                new_f = new_g + h(next_pos)
                new_path = path + [next_pos]
                
                heapq.heappush(open_set, (new_f, new_g, next_pos, new_path))
        
        # 경로 없음 - 목표를 failed에 추가
        if hasattr(self, '_failed_goals'):
            self._failed_goals.add(goal)
        return []
    
    def _calc_party_hp(self, state: Dict[str, Any]) -> float:
        """파티 HP% 계산"""
        party = state.get('party', [])
        if not party:
            return 100
        total = sum(p.get('hp_pct', 100) for p in party)
        return total / len(party)
    
    def _find_walkable_toward(self, px: int, py: int, tx: int, ty: int, min_dist: int, max_dist: int):
        """목표 방향으로 min_dist~max_dist 거리의 탐색된 바닥 타일 찾기"""
        if not self._explored_map:
            return None
        
        best_pos = None
        best_score = float('inf')
        
        for pos in self._explored_map.keys():
            # 현재 위치와의 거리
            dist_from_current = abs(pos[0] - px) + abs(pos[1] - py)
            
            # 거리 범위 체크
            if dist_from_current < min_dist or dist_from_current > max_dist:
                continue
            
            # 목표 방향과의 정렬도 계산 (목표에 가까울수록 좋음)
            dist_to_target = abs(pos[0] - tx) + abs(pos[1] - ty)
            
            # 점수: 목표에 가까울수록 낮음
            score = dist_to_target
            
            if score < best_score:
                best_score = score
                best_pos = pos
        
        return best_pos
    
    def _handle_destroy_item(self, state: Dict[str, Any]) -> str:
        """아이템 파괴 처리 - V 키로 파괴"""
        if not hasattr(self, '_destroy_step'):
            self._destroy_step = 0
        
        mode = getattr(self, '_destroy_mode', None)
        target_idx = getattr(self, '_destroy_target_idx', 0)
        target_name = getattr(self, '_destroy_target_name', '')
        
        print(f"  [파괴] 모드: {mode}, 단계: {self._destroy_step}, 타겟: {target_name} (idx:{target_idx})")
        
        # 타임아웃 (15단계 넘어가면 취소)
        if self._destroy_step > 15:
            print("  [파괴] 타임아웃 - 취소")
            self._destroy_mode = None
            self._destroy_step = 0
            return 'cancel'
        
        self._destroy_step += 1
        
        if mode == 'opening':
            # 인벤토리 열림 대기
            print("  [파괴] 인벤토리 열림 대기")
            self._destroy_mode = 'navigating'
            return None
        
        elif mode == 'navigating':
            # 타겟 아이템까지 이동
            current_step = self._destroy_step - 2
            if current_step < target_idx:
                print(f"  [파괴] 아이템으로 이동 ({current_step}/{target_idx})")
                return 'down'
            else:
                print(f"  [파괴] 아이템 도착: {target_name}")
                self._destroy_mode = 'destroying'
                return None
        
        elif mode == 'destroying':
            # V 키로 파괴
            print(f"  [파괴] 💥 아이템 파괴: {target_name}")
            self._destroy_mode = 'confirming'
            return 'v'  # V 키
        
        elif mode == 'confirming':
            # 파괴 확인
            print("  [파괴] 파괴 확인")
            self._destroy_mode = 'done'
            return 'confirm'
        
        elif mode == 'done':
            # 완료 - 더 파괴할 것 있는지 확인
            destroyable_items = state.get('destroyable_items', [])
            is_overweight = state.get('is_overweight', False)
            
            if is_overweight and len(destroyable_items) > 1:
                # 아직 무거우면 다음 아이템 파괴
                print("  [파괴] 아직 무거움 - 다음 아이템")
                self._destroy_mode = 'navigating'
                self._destroy_step = 2  # 이미 인벤토리 열려있음
                self._destroy_target_idx = destroyable_items[1].get('index', 0) - target_idx
                self._destroy_target_name = destroyable_items[1].get('name', '')
                return None
            else:
                # 완료 - 인벤토리 닫기
                print("  [파괴] 파괴 완료 - 인벤토리 닫기")
                self._destroy_mode = None
                self._destroy_step = 0
                self._destroy_target_idx = 0
                self._destroy_target_name = ''
                return 'cancel'
        
        # 알 수 없는 상태
        print("  [파괴] 알 수 없는 상태 - 취소")
        self._destroy_mode = None
        self._destroy_step = 0
        return 'cancel'
    
    def _handle_inventory(self, state: Dict[str, Any]) -> str:
        """인벤토리 처리 - 아이템 사용/장비 교체"""
        if not hasattr(self, '_inventory_step'):
            self._inventory_step = 0
        
        mode = getattr(self, '_inventory_mode', None)
        target_item = getattr(self, '_inventory_target_item', None)
        
        print(f"  [인벤토리] 모드: {mode}, 단계: {self._inventory_step}, 타겟: {target_item}")
        
        # 타임아웃 (10단계 넘어가면 취소)
        if self._inventory_step > 10:
            print("  [인벤토리] 타임아웃 - 취소")
            self._inventory_mode = None
            self._inventory_step = 0
            return 'cancel'
        
        self._inventory_step += 1
        
        if mode == 'opening':
            # 인벤토리 열림 대기
            print("  [인벤토리] 인벤토리 열림 대기")
            self._inventory_mode = 'searching'
            return None  # 잠시 대기
        
        elif mode == 'searching':
            # 아이템 찾기 - 일단 아래로 이동하면서 찾기
            # 실제로는 메뉴 시스템 상태를 봐야 하지만, 간단히 confirm으로 진행
            inventory = state.get('inventory', [])
            
            # 첫 번째 회복 아이템 선택 시도
            for i, item in enumerate(inventory):
                if target_item and target_item.lower() in item.get('name', '').lower():
                    # 아이템 인덱스만큼 이동
                    if self._inventory_step <= i + 2:
                        print(f"  [인벤토리] 아이템 찾기 ({self._inventory_step-2}/{i})")
                        return 'down'
                    else:
                        self._inventory_mode = 'using'
                        print(f"  [인벤토리] 아이템 발견: {item.get('name')}")
                        return 'confirm'
            
            # 못 찾으면 첫 번째 아이템 사용 시도
            if self._inventory_step > 3:
                self._inventory_mode = 'using'
                return 'confirm'
            
            return 'down'
        
        elif mode == 'using':
            # 아이템 사용 확인
            print("  [인벤토리] 아이템 사용")
            self._inventory_mode = 'selecting_target'
            return 'confirm'
        
        elif mode == 'selecting_target':
            # 타겟 선택 (가장 HP 낮은 캐릭터)
            party = state.get('party', [])
            if party:
                # HP 가장 낮은 캐릭터 찾기
                lowest_idx = 0
                lowest_hp = 100
                for i, p in enumerate(party):
                    if p.get('hp_pct', 100) < lowest_hp:
                        lowest_hp = p.get('hp_pct', 100)
                        lowest_idx = i
                
                # 해당 인덱스까지 이동
                current_step = self._inventory_step - 5  # 대략적인 시작점
                if current_step < lowest_idx:
                    print(f"  [인벤토리] 타겟 이동 ({current_step}/{lowest_idx})")
                    return 'down'
            
            print("  [인벤토리] 타겟 선택 완료")
            self._inventory_mode = 'done'
            return 'confirm'
        
        elif mode == 'done':
            # 완료 - 인벤토리 닫기
            print("  [인벤토리] 완료 - 닫기")
            self._inventory_mode = None
            self._inventory_step = 0
            self._inventory_target_item = None
            return 'cancel'
        
        # 알 수 없는 상태 - 취소
        print("  [인벤토리] 알 수 없는 상태 - 취소")
        self._inventory_mode = None
        self._inventory_step = 0
        return 'cancel'
    
    def _decide_menu(self, state: Dict[str, Any]) -> str:
        """메뉴 행동 결정"""
        menu_type = state.get('menu_type', '').lower()
        screen_text = state.get('screen_text', '').lower()
        
        print(f"[메뉴] 타입: {menu_type}")
        
        # 대화/결과/확인 창 - 자동 진행
        if any(kw in menu_type for kw in ['dialog', 'result', 'victory', 'defeat', 'confirm', 'message']):
            print("  → 자동 진행")
            return 'confirm'
        
        if any(kw in screen_text for kw in ['승리', 'victory', '획득', '클리어', '결과']):
            print("  → 결과 화면 진행")
            return 'confirm'
        
        if menu_type == 'action_menu':
            # 전투 메뉴 - 첫 번째 선택
            return 'confirm'
        elif menu_type == 'target_select':
            # 타겟 선택 - 확인
            return 'confirm'
        elif menu_type == 'inventory':
            # 인벤토리 - 인벤토리 핸들러로 위임
            if not hasattr(self, '_inventory_mode') or not self._inventory_mode:
                self._inventory_mode = 'searching'
            return self._handle_inventory(state)
        elif menu_type == 'shop':
            # 상점 - 나가기
            print("  → 상점 나가기")
            return 'cancel'
        else:
            # 기본 - 확인
            return 'confirm'
    
    def run_once(self) -> bool:
        """한 번 실행"""
        # 항상 상태 읽기 시도 (갱신 없어도 캐시된 상태 사용)
        state = self.read_game_state(force=True)
        if not state:
            return False
        
        # 상태 출력
        mode = state.get('mode', 'unknown')
        floor = state.get('floor', 0) + 1  # 0-indexed → 1-indexed
        ui_state = state.get('ui_state', '')
        
        # 행동 결정
        self._fast_mode = False  # 고속 모드 리셋
        action = self.decide_action(state)
        
        # None이면 입력 안 함 (대기 상태)
        if action is None:
            return True  # 상태는 읽었으니 True
        
        # 고속 모드면 짧은 로그
        if not getattr(self, '_fast_mode', False):
            print(f"🤖 결정: {action}")
        
        # 키 입력
        self.press_key(action)
        return True
    
    def run(self):
        """봇 실행 루프"""
        print("=" * 50)
        print("🤖 Dawn of Stellar - 봇 클라이언트")
        print(f"모델: {self.model}")
        print(f"상태 파일: {GAME_STATE_FILE}")
        print("=" * 50)
        
        # 봇 활성화 파일 생성
        ENABLE_FILE.parent.mkdir(parents=True, exist_ok=True)
        ENABLE_FILE.touch()
        print(f"✅ 봇 활성화 파일 생성: {ENABLE_FILE}")
        
        print("\n게임을 실행하세요. (이미 실행 중이면 게임 창을 클릭하세요)")
        print("중지: Ctrl+C\n")
        
        self.running = True
        wait_count = 0
        last_mode = None
        
        try:
            while self.running:
                if self.run_once():
                    wait_count = 0
                    # 고속 모드면 빠른 딜레이 (0.05초), 아니면 기본 딜레이
                    if getattr(self, '_fast_mode', False):
                        time.sleep(0.05)
                    else:
                        time.sleep(self.delay)
                else:
                    wait_count += 1
                    if wait_count % 20 == 1:
                        print("⏳ 게임 상태 대기 중... (게임을 실행했는지 확인하세요)")
                    time.sleep(0.3)
                    
        except KeyboardInterrupt:
            print("\n⏹️ 봇 종료")
        finally:
            self.running = False


def enable_bot():
    """봇 활성화 파일 생성"""
    ENABLE_FILE.parent.mkdir(parents=True, exist_ok=True)
    ENABLE_FILE.touch()
    print(f"✅ 봇 활성화됨: {ENABLE_FILE}")
    print("이제 게임을 실행하면 봇이 작동합니다.")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Dawn of Stellar 봇 클라이언트")
    parser.add_argument('--model', default='gpt-oss:20b', help='LLM 모델')
    parser.add_argument('--delay', type=float, default=0.2, help='행동 간격 (초)')
    parser.add_argument('--enable', action='store_true', help='봇 활성화만 (실행 안 함)')
    
    args = parser.parse_args()
    
    if args.enable:
        enable_bot()
        return
    
    bot = BotClient(model=args.model, delay=args.delay)
    bot.run()


if __name__ == "__main__":
    main()
