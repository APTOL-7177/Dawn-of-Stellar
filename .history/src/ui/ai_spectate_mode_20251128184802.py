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
    AI 관전 모드 실행
    
    Returns:
        결과 딕셔너리
    """
    from src.multiplayer.llm_player_bot import (
        create_auto_play_ai,
        get_available_jobs,
        TownState,
        ExplorationState,
        PlayStyle
    )
    
    logger.info("AI 관전 모드 시작")
    
    # UI 초기화
    ui = AISpectateUI(console)
    ui.add_commentary("AI 관전 모드 시작!", "success")
    
    # AI 생성
    ui.add_commentary("AI 초기화 중...", "thinking")
    try:
        ai = create_auto_play_ai(model="qwen3:0.6b", style=PlayStyle.BALANCED)
        ui.add_commentary("AI 준비 완료!", "success")
    except Exception as e:
        ui.add_commentary(f"AI 초기화 실패: {e}", "warning")
        logger.error(f"AI 초기화 실패: {e}")
        return {"success": False, "error": str(e)}
    
    # 파티 구성
    ui.add_commentary("파티 구성 추천 중...", "thinking")
    available_jobs = get_available_jobs()
    party_choices = ai.recommend_party(available_jobs, 4)
    
    for choice in party_choices:
        ui.add_commentary(f"파티원: {choice.character_name} ({choice.job_id})", "action")
    
    # 시뮬레이션 루프
    running = True
    simulation_speed = 1.0  # 초당 행동 수
    last_action_time = time.time()
    
    # 데모 상태
    demo_floor = 1
    demo_hp = 100
    demo_battles = 0
    
    while running:
        # 입력 처리
        for event in tcod.event.get():
            if isinstance(event, tcod.event.Quit):
                running = False
            elif isinstance(event, tcod.event.KeyDown):
                if event.sym == tcod.event.KeySym.ESCAPE:
                    running = False
                elif event.sym == tcod.event.KeySym.SPACE:
                    # 속도 조절
                    simulation_speed = 0.5 if simulation_speed == 1.0 else 1.0
                    ui.add_commentary(f"속도: {'빠름' if simulation_speed == 0.5 else '보통'}", "action")
        
        # 시뮬레이션 업데이트
        current_time = time.time()
        if current_time - last_action_time >= simulation_speed:
            last_action_time = current_time
            
            # 데모 시뮬레이션 (실제 게임 연동 시 교체)
            import random
            action_type = random.choice(["explore", "battle", "rest", "item"])
            
            if action_type == "explore":
                direction = random.choice(["북", "남", "동", "서"])
                ui.current_action = f"이동 중 ({direction})"
                ui.add_commentary(f"{direction}쪽으로 이동", "action")
                
                # 랜덤 이벤트
                if random.random() < 0.3:
                    demo_battles += 1
                    ui.add_commentary("적 발견!", "warning")
                    
            elif action_type == "battle":
                if random.random() < 0.7:
                    ui.stats["battles_won"] += 1
                    ui.add_commentary("전투 승리!", "success")
                    demo_hp = min(100, demo_hp + 10)
                else:
                    demo_hp -= 20
                    if demo_hp <= 0:
                        ui.stats["battles_lost"] += 1
                        ui.add_commentary("전투 패배...", "warning")
                        demo_hp = 100
                        demo_floor = 1
                    else:
                        ui.add_commentary(f"피해를 입음 (HP: {demo_hp}%)", "warning")
                        
            elif action_type == "rest":
                demo_hp = min(100, demo_hp + 30)
                ui.current_action = "휴식 중"
                ui.add_commentary(f"휴식으로 회복 (HP: {demo_hp}%)", "success")
                
            elif action_type == "item":
                ui.current_action = "아이템 사용"
                ui.add_commentary("포션 사용", "action")
                demo_hp = min(100, demo_hp + 20)
            
            # 층 진행
            if demo_battles >= 5:
                demo_floor += 1
                demo_battles = 0
                ui.stats["current_floor"] = demo_floor
                ui.stats["floors_cleared"] += 1
                ui.add_commentary(f"🏔️ {demo_floor}층 도착!", "success")
            
            ui.ai_thinking = random.choice([
                "적의 HP가 낮으니 공격하자",
                "MP가 부족해서 기본 공격",
                "힐러가 위험해 보여",
                "BREAK 기회!",
                "버프 먼저 걸자"
            ])
        
        # 렌더링
        console.clear()
        
        # 제목
        title = "🤖 AI 관전 모드"
        console.print((console.width - len(title)) // 2, 1, title, fg=(255, 215, 0))
        console.print((console.width - 30) // 2, 2, "[ESC] 종료  [SPACE] 속도 조절", fg=(150, 150, 150))
        
        # 해설 패널 (왼쪽)
        ui.render_commentary_panel(2, 5, 35, 15)
        
        # 통계 패널 (오른쪽 상단)
        ui.render_stats_panel(45, 5, 30)
        
        # 현재 행동 (하단)
        ui.render_current_action(2, 22)
        
        # 파티 정보 (오른쪽)
        console.print(45, 10, "📦 파티 구성:", fg=(200, 200, 255))
        for i, choice in enumerate(party_choices):
            console.print(45, 11 + i, f"  {choice.character_name} ({choice.job_id})", fg=(180, 180, 180))
        
        # HP 바
        hp_bar_width = 20
        hp_filled = int(hp_bar_width * demo_hp / 100)
        hp_bar = "█" * hp_filled + "░" * (hp_bar_width - hp_filled)
        hp_color = (100, 255, 100) if demo_hp > 50 else ((255, 200, 100) if demo_hp > 25 else (255, 100, 100))
        console.print(45, 16, f"HP: [{hp_bar}] {demo_hp}%", fg=hp_color)
        
        context.present(console)
        
        # 프레임 제한
        time.sleep(0.05)
    
    # 정리
    ai.shutdown()
    logger.info("AI 관전 모드 종료")
    
    return {
        "success": True,
        "stats": ui.stats
    }
