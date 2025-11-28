"""
LLM 기반 고급 플레이어 봇
Dawn of Stellar

Ollama를 사용하여 로컬 LLM으로 고급 플레이어처럼 게임을 플레이하는 AI 봇입니다.
모든 게임 기능(전투, 스킬, 아이템, 요리, 직업 기믹)을 완벽히 활용합니다.
"""

import json
import time
import asyncio
import httpx
from typing import Dict, Any, Optional, List, Tuple, Callable
from collections import deque
from concurrent.futures import ThreadPoolExecutor, Future
import threading
import re
from dataclasses import dataclass, field, asdict
from enum import Enum

from src.core.logger import get_logger
from src.tutorial.tutorial_bot import JOB_DATABASE, COOKING_DATABASE, STATUS_EFFECTS

logger = get_logger("llm_player_bot")


# =============================================================================
# 설정
# =============================================================================

class PlayStyle(Enum):
    """플레이 스타일"""
    AGGRESSIVE = "aggressive"      # 공격적 - 리스크 감수, 높은 딜
    DEFENSIVE = "defensive"        # 방어적 - 안정적, 힐링 우선
    BALANCED = "balanced"          # 균형 - 상황 대응
    SPEEDRUN = "speedrun"          # 스피드런 - 빠른 클리어 우선
    RESOURCE_SAVER = "resource"    # 자원 절약 - MP/아이템 아끼기


@dataclass
class LLMConfig:
    """LLM 설정"""
    base_url: str = "http://localhost:11434"  # Ollama 기본 주소
    model: str = "qwen3:0.6b"  # 사용할 모델 (0.6b=빠름, 1.7b=균형, 4b=똑똑)
    temperature: float = 0.3  # 낮을수록 일관된 결정
    timeout: float = 15.0  # 타임아웃 (초)
    max_tokens: int = 1024  # 최대 출력 토큰
    context_length: int = 2048  # 컨텍스트 길이
    num_gpu: int = 99  # GPU 레이어 수 (최대 = 최고 속도)
    retry_count: int = 3  # 재시도 횟수
    enable_thinking: bool = False  # Qwen3 thinking 모드
    play_style: PlayStyle = PlayStyle.BALANCED  # 플레이 스타일
    enable_commentary: bool = True  # 실시간 해설 활성화
    async_mode: bool = True  # 비동기 모드
    detailed_prompt: bool = False  # True=상세 프롬프트 (느리지만 정확), False=간소화 (빠름)
    boss_mode: bool = False  # 보스전용 상세 분석 모드


# =============================================================================
# 게임 상태 직렬화
# =============================================================================

@dataclass
class TraitInfo:
    """특성 정보"""
    id: str
    name: str
    description: str = ""
    effect_type: str = ""  # stat_bonus, trigger, combat
    

@dataclass
class CombatantState:
    """전투원 상태"""
    name: str
    job: str
    hp: int
    max_hp: int
    mp: int
    max_mp: int
    brv: int
    max_brv: int
    atb_percent: float
    is_alive: bool
    is_broken: bool
    status_effects: List[str] = field(default_factory=list)
    # 직업 기믹 정보
    gimmick_value: int = 0
    gimmick_name: str = ""
    gimmick_max: int = 100  # 기믹 최대치
    # 추가 정보
    element_weakness: str = ""  # 원소 약점 (fire, ice 등)
    element_resistance: str = ""  # 원소 저항
    buffs: List[str] = field(default_factory=list)  # 활성 버프
    debuffs: List[str] = field(default_factory=list)  # 활성 디버프
    can_act: bool = True  # 행동 가능 여부 (기절/수면 시 False)
    # 특성 정보
    traits: List[str] = field(default_factory=list)  # 활성 특성 ID 목록
    trait_effects: List[str] = field(default_factory=list)  # 특성 효과 설명


@dataclass
class SkillInfo:
    """스킬 정보"""
    id: str
    name: str
    mp_cost: int
    skill_type: str  # "brv", "hp", "brv_hp", "heal", "buff", "debuff"
    element: str = "none"
    target_type: str = "single"  # "single", "all", "self"
    description: str = ""
    cooldown_remaining: int = 0


@dataclass  
class ItemInfo:
    """아이템 정보"""
    id: str
    name: str
    quantity: int
    effect: str


@dataclass
class CombatState:
    """전투 상태 전체"""
    turn_count: int
    current_actor: str  # 현재 행동할 캐릭터 이름
    allies: List[CombatantState]
    enemies: List[CombatantState]
    available_skills: List[SkillInfo]
    available_items: List[ItemInfo]
    can_flee: bool = True
    environment: str = ""  # 던전 환경 (숲, 동굴 등)
    boss_name: Optional[str] = None  # 보스전인 경우
    # 팀 상태
    teamwork_gauge: int = 0  # 팀워크 게이지 (0-100)
    active_cooking_buff: str = ""  # 활성 요리 버프
    party_buffs: List[str] = field(default_factory=list)  # 파티 전체 버프


@dataclass
class ExplorationState:
    """탐험 상태"""
    current_floor: int
    current_position: Tuple[int, int]
    visible_tiles: List[Dict[str, Any]]  # 주변 타일 정보
    discovered_rooms: int
    total_rooms: int
    nearby_enemies: List[str]
    nearby_items: List[str]
    nearby_exits: List[Tuple[int, int]]
    party_hp_percent: float  # 파티 평균 HP%
    party_mp_percent: float  # 파티 평균 MP%
    has_healing_point: bool
    floor_type: str  # "forest", "cave", "dungeon" 등
    # 추가 탐험 정보
    stairs_down_position: Optional[Tuple[int, int]] = None  # 하층 계단 위치
    stairs_up_position: Optional[Tuple[int, int]] = None  # 상층 계단 위치
    treasure_positions: List[Tuple[int, int]] = field(default_factory=list)  # 보물 위치
    trap_positions: List[Tuple[int, int]] = field(default_factory=list)  # 함정 위치
    unexplored_directions: List[Tuple[int, int]] = field(default_factory=list)  # 미탐험 방향


@dataclass
class ExplorationAction:
    """탐험 행동"""
    action_type: str  # "move", "interact", "rest", "use_item", "flee", "fight"
    direction: Optional[Tuple[int, int]] = None  # 이동 방향
    target: Optional[str] = None  # 상호작용 대상
    reasoning: str = ""


@dataclass
class PartySetupChoice:
    """파티 구성 선택"""
    job_id: str
    character_name: str
    traits: List[str] = field(default_factory=list)  # 선택할 특성 ID
    reasoning: str = ""


@dataclass
class BattleMemory:
    """전투 기억 - 보스 패턴, 실패 원인 등"""
    enemy_name: str
    attack_patterns: List[str] = field(default_factory=list)
    weaknesses: List[str] = field(default_factory=list)
    dangerous_moves: List[str] = field(default_factory=list)
    successful_strategies: List[str] = field(default_factory=list)
    failed_strategies: List[str] = field(default_factory=list)
    times_fought: int = 0
    times_won: int = 0


@dataclass
class PartyStrategy:
    """파티 전체 전략"""
    tank_target: Optional[str] = None  # 탱커가 도발할 대상
    focus_target: Optional[str] = None  # 집중 공격 대상
    healer_priority: List[str] = field(default_factory=list)  # 힐 우선순위
    buff_priority: List[str] = field(default_factory=list)  # 버프 우선순위
    emergency_plan: str = ""  # 위기 상황 대응 계획


# =============================================================================
# 행동 정의
# =============================================================================

class ActionType(Enum):
    """행동 타입"""
    BRV_ATTACK = "brv_attack"
    HP_ATTACK = "hp_attack"
    SKILL = "skill"
    ITEM = "item"
    DEFEND = "defend"
    FLEE = "flee"


@dataclass
class BotAction:
    """봇 행동"""
    action_type: ActionType
    target_name: Optional[str] = None
    skill_id: Optional[str] = None
    item_id: Optional[str] = None
    reasoning: str = ""  # LLM의 판단 이유
    commentary: str = ""  # 실시간 해설 (플레이어에게 표시)
    thinking: str = ""  # LLM의 추론 과정 (Qwen3 thinking 모드)


# =============================================================================
# 프롬프트 템플릿
# =============================================================================

SYSTEM_PROMPT_BASE = """게임 AI. ATB+BRV 전투 시스템.

## 규칙
1. BRV 공격 → BRV 쌓기 → HP 공격으로 데미지
2. 적 BRV 0 = BREAK → HP 공격 시 보너스
3. 아군 HP 30% 이하 = 위험 → 회복 우선
4. 직업 기믹 활용 (스탠스, 충전, 스택 등)
5. 상태이상: 독/화상=DoT, 기절=행동불가, 버프=강화

## 행동 우선순위
1. 위험 아군 회복 (HP < 30%)
2. BREAK된 적에게 HP 공격
3. 내 BRV 높으면 HP 공격
4. 적 BRV 낮으면 BRV 공격으로 BREAK
5. 스킬로 버프/디버프
6. 기본 BRV 공격

JSON: {"action":"brv_attack|hp_attack|skill|item|defend","target":"대상","skill_id":"스킬ID","reasoning":"이유"}
"""

# 플레이 스타일별 추가 프롬프트 (간소화)
STYLE_PROMPTS = {
    PlayStyle.AGGRESSIVE: "공격적: HP공격 우선, 리스크 감수",
    PlayStyle.DEFENSIVE: "방어적: HP 50% 이하면 회복 우선",
    PlayStyle.BALANCED: "균형: 상황 대응",
    PlayStyle.SPEEDRUN: "스피드: 빠른 처치",
    PlayStyle.RESOURCE_SAVER: "절약: 스킬/아이템 아끼기",
}

RESPONSE_FORMAT = ""  # 시스템 프롬프트에 이미 포함

EXPLORATION_SYSTEM_PROMPT = """당신은 Dawn of Stellar 게임의 던전 탐험 전문가입니다.
최적의 경로로 던전을 탐험하고, 위험을 피하며, 자원을 효율적으로 관리합니다.

## 탐험 규칙
1. 파티 HP/MP가 낮으면 회복 포인트로 이동
2. 출구를 찾되, 모든 방을 탐험하면 보상이 늘어남
3. 강한 적은 피하거나, 준비된 상태에서 교전
4. 아이템/보물 상자는 적극적으로 수집

## 응답 형식 (JSON)
```json
{
  "action": "move" | "interact" | "rest" | "use_item",
  "direction": [dx, dy] (이동 시),
  "target": "상호작용 대상 (선택)",
  "reasoning": "판단 이유"
}
```
"""

PARTY_STRATEGY_PROMPT = """## 파티 전체 전략 수립
현재 파티 구성과 적 상황을 분석하여 팀 전략을 결정하세요.

### 역할 분담
- **탱커**: 도발로 적 어그로 유지, 파티 보호
- **힐러**: 파티 HP 관리, 상태이상 해제
- **딜러**: 집중 공격 대상에 화력 집중
- **서포터**: 버프/디버프로 팀 지원

## 응답 형식 (JSON)
```json
{
  "tank_target": "탱커가 도발할 적 이름",
  "focus_target": "파티가 집중 공격할 적 이름",
  "healer_priority": ["힐 우선순위 캐릭터 목록"],
  "buff_priority": ["버프 우선순위 캐릭터 목록"],
  "emergency_plan": "위기 상황 대응 계획"
}
```
"""


def get_system_prompt(
    style: PlayStyle = PlayStyle.BALANCED, 
    enable_commentary: bool = True,
    enable_thinking: bool = False
) -> str:
    """플레이 스타일에 맞는 시스템 프롬프트 생성 (간소화)"""
    prompt = SYSTEM_PROMPT_BASE + STYLE_PROMPTS.get(style, "")
    return prompt


# 하위 호환성을 위한 기본 프롬프트
SYSTEM_PROMPT = get_system_prompt(PlayStyle.BALANCED)


def create_combat_prompt(state: CombatState, job_info: Dict[str, Any], detailed: bool = False) -> str:
    """
    전투 상황 프롬프트 생성
    
    Args:
        state: 전투 상태
        job_info: 직업 정보
        detailed: True면 상세 정보 포함 (느리지만 정확)
    """
    # 현재 캐릭터
    current = None
    for ally in state.allies:
        if ally.name == state.current_actor:
            current = ally
            break
    
    if not current:
        return "행동 캐릭터 없음"
    
    # === 간소화 모드 (빠른 응답) ===
    if not detailed:
        # 현재 캐릭터
        hp_pct = int(current.hp / current.max_hp * 100) if current.max_hp > 0 else 0
        me = f"{current.name}({current.job}):HP{hp_pct}% BRV{current.brv}"
        if current.gimmick_name:
            me += f" {current.gimmick_name}:{current.gimmick_value}"
        
        # 적 상태
        enemies = []
        for e in state.enemies:
            if e.is_alive:
                e_hp = int(e.hp / e.max_hp * 100) if e.max_hp > 0 else 0
                status = "[BREAK]" if e.is_broken else ""
                enemies.append(f"{e.name}:HP{e_hp}% BRV{e.brv}{status}")
        
        # 위험한 아군
        low_hp_allies = [a.name for a in state.allies if a.is_alive and a.hp < a.max_hp * 0.3]
        
        # 스킬
        skills = []
        for s in state.available_skills[:5]:
            skills.append(f"{s.id}(MP{s.mp_cost})")
        
        prompt = f"""나:{me}
적:{','.join(enemies)}
{"위험:" + ','.join(low_hp_allies) if low_hp_allies else ""}
스킬:{','.join(skills)}
행동(JSON):"""
        return prompt
    
    # === 상세 모드 ===
    lines = [f"## 턴 {state.turn_count} - {state.current_actor} 행동"]
    
    # 현재 캐릭터 상세
    hp_pct = int(current.hp / current.max_hp * 100)
    lines.append(f"\n### 나: {current.name} ({current.job})")
    lines.append(f"HP:{current.hp}/{current.max_hp}({hp_pct}%) MP:{current.mp}/{current.max_mp} BRV:{current.brv}/{current.max_brv}")
    if current.gimmick_name:
        lines.append(f"기믹: {current.gimmick_name} = {current.gimmick_value}")
    if current.status_effects:
        lines.append(f"상태: {', '.join(current.status_effects)}")
    
    # 아군 상태
    lines.append("\n### 아군")
    for ally in state.allies:
        if ally.name == current.name:
            continue
        if not ally.is_alive:
            lines.append(f"- {ally.name}: 사망")
            continue
        hp_pct = int(ally.hp / ally.max_hp * 100)
        status = "BREAK" if ally.is_broken else ""
        lines.append(f"- {ally.name}({ally.job}): HP{hp_pct}% BRV{ally.brv} {status}")
    
    # 적 상태
    lines.append("\n### 적")
    for enemy in state.enemies:
        if not enemy.is_alive:
            continue
        hp_pct = int(enemy.hp / enemy.max_hp * 100)
        status = "[BREAK!]" if enemy.is_broken else ""
        effects = f" ({', '.join(enemy.status_effects)})" if enemy.status_effects else ""
        lines.append(f"- {enemy.name}: HP{hp_pct}% BRV{enemy.brv} {status}{effects}")
    
    # 스킬
    if state.available_skills:
        lines.append("\n### 스킬")
        for skill in state.available_skills[:6]:
            cd = f" (쿨{skill.cooldown_remaining})" if skill.cooldown_remaining > 0 else ""
            lines.append(f"- {skill.id}: {skill.name} MP{skill.mp_cost} {skill.skill_type}{cd}")
    
    # 아이템
    if state.available_items:
        lines.append("\n### 아이템")
        for item in state.available_items[:4]:
            lines.append(f"- {item.id}: {item.name} x{item.quantity}")
    
    lines.append("\n행동 선택(JSON):")
    return "\n".join(lines)


# =============================================================================
# Ollama 클라이언트
# =============================================================================

class OllamaClient:
    """Ollama API 클라이언트"""
    
    def __init__(self, config: LLMConfig):
        self.config = config
        self.client = httpx.AsyncClient(timeout=config.timeout)
    
    async def generate(self, prompt: str, system_prompt: str = "") -> str:
        """텍스트 생성"""
        url = f"{self.config.base_url}/api/generate"
        
        payload = {
            "model": self.config.model,
            "prompt": prompt,
            "system": system_prompt,
            "stream": False,
            "options": {
                "temperature": self.config.temperature,
                "num_predict": self.config.max_tokens,
                "num_ctx": self.config.context_length,
                "num_gpu": self.config.num_gpu,
            }
        }
        
        for attempt in range(self.config.retry_count + 1):
            try:
                response = await self.client.post(url, json=payload)
                response.raise_for_status()
                result = response.json()
                return result.get("response", "")
            except Exception as e:
                logger.warning(f"Ollama 요청 실패 (시도 {attempt + 1}): {e}")
                if attempt == self.config.retry_count:
                    raise
                await asyncio.sleep(1)
        
        return ""
    
    async def chat(self, messages: List[Dict[str, str]]) -> str:
        """채팅 형식 생성"""
        url = f"{self.config.base_url}/api/chat"
        
        payload = {
            "model": self.config.model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": self.config.temperature,
                "num_predict": self.config.max_tokens,
                "num_ctx": self.config.context_length,
                "num_gpu": self.config.num_gpu,
            }
        }
        
        for attempt in range(self.config.retry_count + 1):
            try:
                response = await self.client.post(url, json=payload)
                response.raise_for_status()
                result = response.json()
                return result.get("message", {}).get("content", "")
            except Exception as e:
                logger.warning(f"Ollama 채팅 요청 실패 (시도 {attempt + 1}): {e}")
                if attempt == self.config.retry_count:
                    raise
                await asyncio.sleep(1)
        
        return ""
    
    async def close(self):
        """클라이언트 종료"""
        await self.client.aclose()


# =============================================================================
# 동기 래퍼 (게임 루프에서 사용)
# =============================================================================

class OllamaClientSync:
    """동기 Ollama 클라이언트 (게임 루프용)"""
    
    def __init__(self, config: LLMConfig):
        self.config = config
    
    def generate(self, prompt: str, system_prompt: str = "") -> str:
        """동기 텍스트 생성"""
        import httpx
        
        url = f"{self.config.base_url}/api/generate"
        
        payload = {
            "model": self.config.model,
            "prompt": prompt,
            "system": system_prompt,
            "stream": False,
            "options": {
                "temperature": self.config.temperature,
                "num_predict": self.config.max_tokens,
                "num_ctx": self.config.context_length,
                "num_gpu": self.config.num_gpu,  # GPU 레이어 수 (소음 감소)
            }
        }
        
        for attempt in range(self.config.retry_count + 1):
            try:
                with httpx.Client(timeout=self.config.timeout) as client:
                    response = client.post(url, json=payload)
                    response.raise_for_status()
                    result = response.json()
                    text = result.get("response", "")
                    
                    # 빈 응답 체크 - 재시도
                    if not text.strip():
                        logger.warning(f"빈 응답 받음 (시도 {attempt + 1})")
                        if attempt < self.config.retry_count:
                            time.sleep(0.5)
                            continue
                    
                    return text
            except Exception as e:
                logger.warning(f"Ollama 요청 실패 (시도 {attempt + 1}): {e}")
                if attempt == self.config.retry_count:
                    raise
                time.sleep(1)
        
        return ""


# =============================================================================
# 응답 파서
# =============================================================================

class ResponseParser:
    """LLM 응답 파서 - Thinking 모드 지원"""
    
    @staticmethod
    def extract_thinking(response: str) -> Tuple[str, str]:
        """
        Qwen3 thinking 모드 응답에서 추론 과정과 최종 응답 분리
        
        Returns:
            (thinking_content, final_response)
        """
        thinking = ""
        final_response = response
        
        # <think>...</think> 패턴 추출
        think_pattern = r'<think>(.*?)</think>'
        think_match = re.search(think_pattern, response, re.DOTALL)
        
        if think_match:
            thinking = think_match.group(1).strip()
            # thinking 부분 제거
            final_response = re.sub(think_pattern, '', response, flags=re.DOTALL).strip()
        
        return thinking, final_response
    
    @staticmethod
    def parse_action(response: str) -> Optional[BotAction]:
        """LLM 응답을 BotAction으로 파싱 (Thinking 모드 지원)"""
        try:
            # Thinking 추출
            thinking, clean_response = ResponseParser.extract_thinking(response)
            
            # JSON 블록 추출
            json_str = clean_response
            if "```json" in clean_response:
                start = clean_response.find("```json") + 7
                end = clean_response.find("```", start)
                json_str = clean_response[start:end].strip()
            elif "```" in clean_response:
                start = clean_response.find("```") + 3
                end = clean_response.find("```", start)
                json_str = clean_response[start:end].strip()
            elif "{" in clean_response:
                start = clean_response.find("{")
                end = clean_response.rfind("}") + 1
                json_str = clean_response[start:end]
            
            data = json.loads(json_str)
            
            # 액션 타입 파싱
            action_str = data.get("action", "brv_attack").lower()
            action_map = {
                "brv_attack": ActionType.BRV_ATTACK,
                "hp_attack": ActionType.HP_ATTACK,
                "skill": ActionType.SKILL,
                "item": ActionType.ITEM,
                "defend": ActionType.DEFEND,
                "flee": ActionType.FLEE,
            }
            action_type = action_map.get(action_str, ActionType.BRV_ATTACK)
            
            return BotAction(
                action_type=action_type,
                target_name=data.get("target"),
                skill_id=data.get("skill_id"),
                item_id=data.get("item_id"),
                reasoning=data.get("reasoning", ""),
                commentary=data.get("commentary", ""),
                thinking=thinking
            )
            
        except Exception as e:
            logger.error(f"응답 파싱 실패: {e}, 응답: {response[:200]}")
            return None
    
    @staticmethod
    def parse_exploration_action(response: str) -> Optional[ExplorationAction]:
        """탐험 행동 파싱"""
        try:
            thinking, clean_response = ResponseParser.extract_thinking(response)
            
            # JSON 추출
            json_str = clean_response
            if "{" in clean_response:
                start = clean_response.find("{")
                end = clean_response.rfind("}") + 1
                json_str = clean_response[start:end]
            
            data = json.loads(json_str)
            
            direction = None
            if "direction" in data:
                d = data["direction"]
                if isinstance(d, list) and len(d) == 2:
                    direction = (d[0], d[1])
            
            return ExplorationAction(
                action_type=data.get("action", "move"),
                direction=direction,
                target=data.get("target"),
                reasoning=data.get("reasoning", "")
            )
            
        except Exception as e:
            logger.error(f"탐험 행동 파싱 실패: {e}")
            return None
    
    @staticmethod
    def parse_party_strategy(response: str) -> Optional[PartyStrategy]:
        """파티 전략 파싱"""
        try:
            thinking, clean_response = ResponseParser.extract_thinking(response)
            
            # JSON 추출
            json_str = clean_response
            if "{" in clean_response:
                start = clean_response.find("{")
                end = clean_response.rfind("}") + 1
                json_str = clean_response[start:end]
            
            data = json.loads(json_str)
            
            return PartyStrategy(
                tank_target=data.get("tank_target"),
                focus_target=data.get("focus_target"),
                healer_priority=data.get("healer_priority", []),
                buff_priority=data.get("buff_priority", []),
                emergency_plan=data.get("emergency_plan", "")
            )
            
        except Exception as e:
            logger.error(f"파티 전략 파싱 실패: {e}")
            return None


# =============================================================================
# LLM 플레이어 봇
# =============================================================================

class LLMPlayerBot:
    """LLM 기반 고급 플레이어 봇 - 전투, 탐험, 파티 전략 지원"""
    
    def __init__(
        self,
        bot_id: str,
        bot_name: str,
        job_id: str = "warrior",
        config: Optional[LLMConfig] = None
    ):
        """
        Args:
            bot_id: 봇 ID
            bot_name: 봇 이름
            job_id: 직업 ID
            config: LLM 설정
        """
        self.bot_id = bot_id
        self.bot_name = bot_name
        self.job_id = job_id
        self.config = config or LLMConfig()
        
        self.client = OllamaClientSync(self.config)
        self.parser = ResponseParser()
        
        # 직업 정보 캐싱
        self.job_info = JOB_DATABASE.get(job_id, JOB_DATABASE.get("default", {}))
        
        # 전투 기록 (컨텍스트용)
        self.combat_history: List[str] = []
        self.max_history = 10
        
        # 🧠 전투 기억 시스템 - 보스 패턴, 약점 등 학습
        self.battle_memories: Dict[str, BattleMemory] = {}
        
        # 👥 파티 전략
        self.current_strategy: Optional[PartyStrategy] = None
        
        # ⚡ 비동기 처리
        self._executor: Optional[ThreadPoolExecutor] = None
        self._pending_action: Optional[Future] = None
        self._action_ready = threading.Event()
        self._cached_action: Optional[BotAction] = None
        
        # 💬 해설 콜백
        self.on_commentary: Optional[Callable[[str], None]] = None
        
        # 통계
        self.total_actions = 0
        self.successful_parses = 0
        self.fallback_actions = 0
        self.thinking_count = 0  # thinking 모드 사용 횟수
        
        # 비동기 모드 초기화
        if self.config.async_mode:
            self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="LLMBot")
        
        logger.info(
            f"LLM 플레이어 봇 생성: {bot_name} "
            f"(직업: {job_id}, 모델: {self.config.model}, "
            f"스타일: {self.config.play_style.value}, "
            f"thinking: {self.config.enable_thinking})"
        )
    
    def _get_system_prompt(self) -> str:
        """현재 설정에 맞는 시스템 프롬프트 생성"""
        return get_system_prompt(
            style=self.config.play_style,
            enable_commentary=self.config.enable_commentary,
            enable_thinking=self.config.enable_thinking
        )
    
    # =========================================================================
    # 전투 기억 시스템
    # =========================================================================
    
    def remember_battle(self, enemy_name: str, won: bool, notes: List[str] = None):
        """전투 결과 기억"""
        if enemy_name not in self.battle_memories:
            self.battle_memories[enemy_name] = BattleMemory(enemy_name=enemy_name)
        
        memory = self.battle_memories[enemy_name]
        memory.times_fought += 1
        if won:
            memory.times_won += 1
            if notes:
                memory.successful_strategies.extend(notes)
        else:
            if notes:
                memory.failed_strategies.extend(notes)
    
    def add_enemy_pattern(self, enemy_name: str, pattern: str):
        """적 공격 패턴 기록"""
        if enemy_name not in self.battle_memories:
            self.battle_memories[enemy_name] = BattleMemory(enemy_name=enemy_name)
        if pattern not in self.battle_memories[enemy_name].attack_patterns:
            self.battle_memories[enemy_name].attack_patterns.append(pattern)
    
    def add_enemy_weakness(self, enemy_name: str, weakness: str):
        """적 약점 기록"""
        if enemy_name not in self.battle_memories:
            self.battle_memories[enemy_name] = BattleMemory(enemy_name=enemy_name)
        if weakness not in self.battle_memories[enemy_name].weaknesses:
            self.battle_memories[enemy_name].weaknesses.append(weakness)
    
    def get_memory_context(self, enemy_names: List[str]) -> str:
        """기억된 적 정보를 컨텍스트로 변환"""
        context = ""
        for name in enemy_names:
            if name in self.battle_memories:
                mem = self.battle_memories[name]
                context += f"\n## 📚 {name} 정보 (전적: {mem.times_won}/{mem.times_fought})\n"
                if mem.weaknesses:
                    context += f"- 약점: {', '.join(mem.weaknesses)}\n"
                if mem.attack_patterns:
                    context += f"- 패턴: {', '.join(mem.attack_patterns[:3])}\n"
                if mem.dangerous_moves:
                    context += f"- ⚠️ 위험 기술: {', '.join(mem.dangerous_moves)}\n"
                if mem.successful_strategies:
                    context += f"- ✅ 효과적 전략: {mem.successful_strategies[-1]}\n"
        return context
    
    # =========================================================================
    # 파티 전략 수립
    # =========================================================================
    
    def plan_party_strategy(self, combat_state: CombatState) -> PartyStrategy:
        """파티 전체 전략 수립"""
        try:
            # 파티 정보 요약
            party_info = "\n".join([
                f"- {a.name} ({a.job}): HP {a.hp}/{a.max_hp}, 역할 추정"
                for a in combat_state.allies if a.is_alive
            ])
            
            enemy_info = "\n".join([
                f"- {e.name}: HP {e.hp}/{e.max_hp}"
                for e in combat_state.enemies if e.is_alive
            ])
            
            prompt = f"""현재 파티:
{party_info}

현재 적:
{enemy_info}

{PARTY_STRATEGY_PROMPT}"""
            
            response = self.client.generate(prompt, self._get_system_prompt())
            strategy = self.parser.parse_party_strategy(response)
            
            if strategy:
                self.current_strategy = strategy
                logger.info(f"[{self.bot_name}] 파티 전략 수립: 집중 타겟={strategy.focus_target}")
                return strategy
            
        except Exception as e:
            logger.error(f"파티 전략 수립 실패: {e}")
        
        # 기본 전략
        return PartyStrategy(
            focus_target=combat_state.enemies[0].name if combat_state.enemies else None
        )
    
    # =========================================================================
    # 비동기 처리
    # =========================================================================
    
    def request_action_async(self, combat_state: CombatState):
        """비동기로 행동 결정 요청 (게임 프레임 드롭 방지)"""
        if not self._executor:
            # 비동기 모드가 아니면 동기 호출
            self._cached_action = self.decide_combat_action(combat_state)
            self._action_ready.set()
            return
        
        self._action_ready.clear()
        self._pending_action = self._executor.submit(
            self.decide_combat_action, combat_state
        )
        
        def on_complete(future):
            try:
                self._cached_action = future.result()
            except Exception as e:
                logger.error(f"비동기 행동 결정 실패: {e}")
                self._cached_action = self._fallback_action(combat_state)
            self._action_ready.set()
        
        self._pending_action.add_done_callback(on_complete)
    
    def get_action_if_ready(self) -> Optional[BotAction]:
        """준비된 행동 반환 (없으면 None)"""
        if self._action_ready.is_set():
            action = self._cached_action
            self._cached_action = None
            self._action_ready.clear()
            return action
        return None
    
    def wait_for_action(self, timeout: float = None) -> Optional[BotAction]:
        """행동이 준비될 때까지 대기"""
        self._action_ready.wait(timeout=timeout)
        return self.get_action_if_ready()
    
    def decide_combat_action(
        self,
        combat_state: CombatState
    ) -> BotAction:
        """
        전투 행동 결정 - 기억, 전략, thinking 모드 통합
        
        Args:
            combat_state: 현재 전투 상태
            
        Returns:
            결정된 행동
        """
        self.total_actions += 1
        
        try:
            # 보스전이거나 상세 모드면 detailed=True
            is_boss = combat_state.boss_name is not None
            use_detailed = self.config.detailed_prompt or (self.config.boss_mode and is_boss)
            
            # 프롬프트 생성
            prompt = create_combat_prompt(combat_state, self.job_info, detailed=use_detailed)
            
            # 🧠 기억된 적 정보 추가
            enemy_names = [e.name for e in combat_state.enemies if e.is_alive]
            memory_context = self.get_memory_context(enemy_names)
            if memory_context:
                prompt = memory_context + "\n" + prompt
            
            # 👥 파티 전략 컨텍스트 추가 (보스전에서만)
            if is_boss and self.current_strategy:
                strategy_text = f"\n## 🎯 파티 전략\n"
                strategy_text += f"- 집중 타겟: {self.current_strategy.focus_target}\n"
                if self.current_strategy.emergency_plan:
                    strategy_text += f"- 위기 대응: {self.current_strategy.emergency_plan}\n"
                prompt = strategy_text + prompt
            
            # 히스토리 추가 (최근 2개만 - 속도 위해)
            if self.combat_history:
                history_text = "최근:" + "/".join(self.combat_history[-2:])
                prompt = history_text + "\n" + prompt
            
            # LLM 호출 (플레이 스타일 반영)
            system_prompt = self._get_system_prompt()
            response = self.client.generate(prompt, system_prompt)
            
            # 응답 파싱
            action = self.parser.parse_action(response)
            
            if action:
                self.successful_parses += 1
                
                # thinking 모드 통계
                if action.thinking:
                    self.thinking_count += 1
                    logger.debug(f"[{self.bot_name}] 🧠 Thinking: {action.thinking[:100]}...")
                
                # 💬 해설 콜백 호출
                if action.commentary and self.on_commentary:
                    self.on_commentary(action.commentary)
                
                # 히스토리 기록
                self.combat_history.append(
                    f"턴 {combat_state.turn_count}: {action.action_type.value} -> {action.target_name or 'N/A'}"
                )
                if len(self.combat_history) > self.max_history:
                    self.combat_history.pop(0)
                
                logger.info(
                    f"[{self.bot_name}] 행동 결정: {action.action_type.value}, "
                    f"타겟: {action.target_name}, 이유: {action.reasoning}"
                )
                return action
            else:
                return self._fallback_action(combat_state)
                
        except Exception as e:
            logger.error(f"[{self.bot_name}] LLM 호출 오류: {e}")
            return self._fallback_action(combat_state)
    
    # =========================================================================
    # 탐험 의사결정
    # =========================================================================
    
    def decide_exploration_action(
        self,
        exploration_state: ExplorationState
    ) -> ExplorationAction:
        """
        탐험 행동 결정
        
        Args:
            exploration_state: 현재 탐험 상태
            
        Returns:
            탐험 행동
        """
        try:
            # 탐험 상황 프롬프트 생성
            prompt = f"""## 현재 탐험 상황 (층: {exploration_state.current_floor})
위치: {exploration_state.current_position}
탐험률: {exploration_state.discovered_rooms}/{exploration_state.total_rooms} 방

### 파티 상태
- HP: {exploration_state.party_hp_percent:.0f}%
- MP: {exploration_state.party_mp_percent:.0f}%

### 주변 정보
- 근처 적: {', '.join(exploration_state.nearby_enemies) or '없음'}
- 근처 아이템: {', '.join(exploration_state.nearby_items) or '없음'}
- 출구: {exploration_state.nearby_exits if exploration_state.nearby_exits else '미발견'}
- 회복 포인트: {'있음' if exploration_state.has_healing_point else '없음'}

### 이동 가능 방향
"""
            for tile in exploration_state.visible_tiles[:8]:
                prompt += f"- {tile.get('direction', '?')}: {tile.get('type', 'unknown')}\n"
            
            prompt += "\n최적의 탐험 행동을 선택하세요:"
            
            response = self.client.generate(prompt, EXPLORATION_SYSTEM_PROMPT)
            action = self.parser.parse_exploration_action(response)
            
            if action:
                logger.info(f"[{self.bot_name}] 탐험 결정: {action.action_type}, 방향: {action.direction}")
                return action
            
        except Exception as e:
            logger.error(f"[{self.bot_name}] 탐험 결정 오류: {e}")
        
        # 폴백: 랜덤 이동
        import random
        directions = [(0, -1), (0, 1), (-1, 0), (1, 0)]
        return ExplorationAction(
            action_type="move",
            direction=random.choice(directions),
            reasoning="폴백: 랜덤 이동"
        )
    
    def _fallback_action(self, combat_state: CombatState) -> BotAction:
        """폴백 행동 (LLM 실패 시)"""
        self.fallback_actions += 1
        
        # 현재 행동자 찾기
        current_ally = None
        for ally in combat_state.allies:
            if ally.name == combat_state.current_actor:
                current_ally = ally
                break
        
        if not current_ally or not current_ally.is_alive:
            return BotAction(
                action_type=ActionType.DEFEND,
                reasoning="폴백: 방어"
            )
        
        # 살아있는 적 찾기
        alive_enemies = [e for e in combat_state.enemies if e.is_alive]
        if not alive_enemies:
            return BotAction(
                action_type=ActionType.DEFEND,
                reasoning="폴백: 적 없음"
            )
        
        target = alive_enemies[0]
        
        # 간단한 규칙 기반 폴백
        # 1. HP 위험하면 회복 아이템
        hp_percent = current_ally.hp / current_ally.max_hp if current_ally.max_hp > 0 else 1.0
        if hp_percent < 0.3:
            for item in combat_state.available_items:
                if "회복" in item.effect or "HP" in item.effect.upper():
                    return BotAction(
                        action_type=ActionType.ITEM,
                        item_id=item.id,
                        target_name=current_ally.name,
                        reasoning="폴백: HP 낮아서 회복"
                    )
        
        # 2. BRV 충분하면 HP 공격
        if current_ally.brv > 500:
            # BREAK 상태인 적 우선
            for enemy in alive_enemies:
                if enemy.is_broken:
                    return BotAction(
                        action_type=ActionType.HP_ATTACK,
                        target_name=enemy.name,
                        reasoning="폴백: BREAK 상태 적에게 HP 공격"
                    )
            return BotAction(
                action_type=ActionType.HP_ATTACK,
                target_name=target.name,
                reasoning="폴백: BRV 높아서 HP 공격"
            )
        
        # 3. 적 BRV 낮으면 BRV 공격으로 BREAK 노리기
        for enemy in alive_enemies:
            if enemy.brv < 200:
                return BotAction(
                    action_type=ActionType.BRV_ATTACK,
                    target_name=enemy.name,
                    reasoning="폴백: 적 BRV 낮아서 BREAK 노림"
                )
        
        # 4. 기본 BRV 공격
        return BotAction(
            action_type=ActionType.BRV_ATTACK,
            target_name=target.name,
            reasoning="폴백: 기본 BRV 공격"
        )
    
    def get_stats(self) -> Dict[str, Any]:
        """상세 통계 반환"""
        success_rate = (self.successful_parses / self.total_actions * 100) if self.total_actions > 0 else 0
        return {
            "bot_name": self.bot_name,
            "job": self.job_id,
            "model": self.config.model,
            "play_style": self.config.play_style.value,
            "total_actions": self.total_actions,
            "successful_parses": self.successful_parses,
            "fallback_actions": self.fallback_actions,
            "thinking_count": self.thinking_count,
            "success_rate": f"{success_rate:.1f}%",
            "memories_count": len(self.battle_memories),
            "async_mode": self.config.async_mode,
        }
    
    def shutdown(self):
        """봇 종료 및 리소스 정리"""
        if self._executor:
            self._executor.shutdown(wait=False)
            self._executor = None
        logger.info(f"[{self.bot_name}] 봇 종료됨")
    
    def __del__(self):
        """소멸자"""
        self.shutdown()
    
    def set_play_style(self, style: PlayStyle):
        """플레이 스타일 변경"""
        self.config.play_style = style
        logger.info(f"[{self.bot_name}] 플레이 스타일 변경: {style.value}")
    
    def set_commentary_callback(self, callback: Callable[[str], None]):
        """해설 콜백 설정"""
        self.on_commentary = callback


# =============================================================================
# 게임 상태 변환 헬퍼
# =============================================================================

class GameStateConverter:
    """게임 객체를 CombatState로 변환"""
    
    @staticmethod
    def from_combat_manager(
        combat_manager: Any,
        current_character: Any,
        inventory: Any = None
    ) -> CombatState:
        """
        CombatManager에서 CombatState 생성
        
        Args:
            combat_manager: 전투 관리자
            current_character: 현재 행동할 캐릭터
            inventory: 인벤토리 (선택)
            
        Returns:
            CombatState
        """
        # 아군 상태 변환
        allies = []
        for ally in combat_manager.allies:
            allies.append(GameStateConverter._convert_combatant(ally))
        
        # 적 상태 변환
        enemies = []
        for enemy in combat_manager.enemies:
            enemies.append(GameStateConverter._convert_combatant(enemy))
        
        # 스킬 변환
        skills = []
        if hasattr(current_character, 'skills'):
            for skill in current_character.skills:
                if hasattr(skill, 'can_use') and skill.can_use(current_character):
                    skills.append(GameStateConverter._convert_skill(skill))
        
        # 아이템 변환
        items = []
        if inventory:
            for item in inventory.get_usable_items():
                items.append(GameStateConverter._convert_item(item))
        
        # 팀워크 게이지 추출
        teamwork_gauge = 0
        if hasattr(combat_manager, 'party') and combat_manager.party:
            teamwork_gauge = getattr(combat_manager.party, 'teamwork_gauge', 0)
        elif hasattr(combat_manager, '_party') and combat_manager._party:
            teamwork_gauge = getattr(combat_manager._party, 'teamwork_gauge', 0)
        
        # 보스 이름 추출 (적 중 is_boss가 True인 경우)
        boss_name = None
        for enemy in combat_manager.enemies:
            if getattr(enemy, 'is_boss', False):
                boss_name = getattr(enemy, 'name', 'Boss')
                break
        
        # 환경 효과 추출
        environment = ""
        if hasattr(combat_manager, 'dungeon') and combat_manager.dungeon:
            environment = getattr(combat_manager.dungeon, 'biome', '')
        
        # 파티 버프 (요리 효과 등)
        party_buffs = []
        cooking_buff = ""
        if hasattr(combat_manager, 'party') and combat_manager.party:
            party = combat_manager.party
            if hasattr(party, 'active_cooking_effect'):
                cooking_buff = getattr(party, 'active_cooking_effect', '')
            if hasattr(party, 'party_buffs'):
                party_buffs = list(party.party_buffs.keys()) if isinstance(party.party_buffs, dict) else party.party_buffs
        
        return CombatState(
            turn_count=combat_manager.turn_count,
            current_actor=getattr(current_character, 'name', 'Unknown'),
            allies=allies,
            enemies=enemies,
            available_skills=skills,
            available_items=items,
            can_flee=True,
            environment=environment,
            boss_name=boss_name,
            teamwork_gauge=teamwork_gauge,
            active_cooking_buff=cooking_buff,
            party_buffs=party_buffs
        )
    
    @staticmethod
    def _convert_combatant(char: Any) -> CombatantState:
        """캐릭터를 CombatantState로 변환 (모든 게임 정보 포함)"""
        # 기믹 정보 추출
        gimmick_value = 0
        gimmick_name = ""
        if hasattr(char, 'gimmick_manager') and char.gimmick_manager:
            gimmick = char.gimmick_manager
            gimmick_name = getattr(gimmick, 'gimmick_name', '')
            gimmick_value = getattr(gimmick, 'current_value', 0)
        # 대체: 직접 기믹 필드 확인
        elif hasattr(char, 'gimmick_type'):
            gimmick_name = getattr(char, 'gimmick_type', '')
            # 일반적인 기믹 값 필드 확인
            for field in ['charge_gauge', 'stance', 'combo_count', 'faith', 'chakra', 
                          'blood_gauge', 'melody_notes', 'shadow_stack', 'rune_count']:
                if hasattr(char, field):
                    gimmick_value = getattr(char, field, 0)
                    break
        
        # 상태이상 추출
        status_effects = []
        buffs = []
        debuffs = []
        can_act = True
        
        if hasattr(char, 'status_manager'):
            sm = char.status_manager
            for effect in getattr(sm, 'status_effects', []):
                effect_name = getattr(effect, 'name', str(effect))
                status_effects.append(effect_name)
                
                # 버프/디버프 분류
                status_type = getattr(effect, 'status_type', None)
                if status_type:
                    type_name = status_type.name if hasattr(status_type, 'name') else str(status_type)
                    if 'BOOST' in type_name or 'REGEN' in type_name or 'HASTE' in type_name:
                        buffs.append(effect_name)
                    elif 'REDUCE' in type_name or 'POISON' in type_name or 'SLOW' in type_name:
                        debuffs.append(effect_name)
            
            # 행동 가능 여부
            can_act = sm.can_act() if hasattr(sm, 'can_act') else True
        elif hasattr(char, 'status_effects'):
            for effect in char.status_effects:
                status_effects.append(getattr(effect, 'name', str(effect)))
        
        # 원소 약점/저항 추출
        element_weakness = ""
        element_resistance = ""
        if hasattr(char, 'element_resistance'):
            for elem, value in char.element_resistance.items():
                if value < 1.0:  # 약점
                    element_weakness = elem
                elif value > 1.0:  # 저항
                    element_resistance = elem
        
        # 특성 정보 추출
        traits = []
        trait_effects = []
        if hasattr(char, 'active_traits'):
            for trait in char.active_traits:
                if isinstance(trait, str):
                    traits.append(trait)
                elif isinstance(trait, dict):
                    traits.append(trait.get('id', ''))
                    if trait.get('description'):
                        trait_effects.append(trait.get('description', '')[:30])
                else:
                    trait_id = getattr(trait, 'id', getattr(trait, 'trait_id', ''))
                    if trait_id:
                        traits.append(trait_id)
        
        # 기믹 최대치 추출
        gimmick_max = 100
        if hasattr(char, 'gimmick_max'):
            gimmick_max = getattr(char, 'gimmick_max', 100)
        elif gimmick_name:
            # 직업별 기믹 최대치 추정
            gimmick_maxes = {
                'stance': 6, 'charge': 100, 'chakra': 7, 'combo': 10,
                'blood': 100, 'faith': 100, 'melody': 8, 'shadow': 5
            }
            for key, max_val in gimmick_maxes.items():
                if key in gimmick_name.lower():
                    gimmick_max = max_val
                    break
        
        return CombatantState(
            name=getattr(char, 'name', 'Unknown'),
            job=getattr(char, 'job_name', getattr(char, 'job_id', getattr(char, 'character_class', 'Unknown'))),
            hp=getattr(char, 'current_hp', 0),
            max_hp=getattr(char, 'max_hp', 1),
            mp=getattr(char, 'current_mp', 0),
            max_mp=getattr(char, 'max_mp', 1),
            brv=getattr(char, 'current_brv', 0),
            max_brv=getattr(char, 'max_brv', 1000),
            atb_percent=getattr(char, 'atb_percent', 0),
            is_alive=getattr(char, 'is_alive', True),
            is_broken=getattr(char, 'is_broken', False),
            status_effects=status_effects,
            gimmick_value=gimmick_value,
            gimmick_name=gimmick_name,
            gimmick_max=gimmick_max,
            element_weakness=element_weakness,
            element_resistance=element_resistance,
            buffs=buffs,
            debuffs=debuffs,
            can_act=can_act,
            traits=traits,
            trait_effects=trait_effects
        )
    
    @staticmethod
    def _convert_skill(skill: Any) -> SkillInfo:
        """스킬을 SkillInfo로 변환"""
        return SkillInfo(
            id=getattr(skill, 'id', getattr(skill, 'skill_id', 'unknown')),
            name=getattr(skill, 'name', 'Unknown'),
            mp_cost=getattr(skill, 'mp_cost', 0),
            skill_type=getattr(skill, 'skill_type', 'brv'),
            element=getattr(skill, 'element', 'none'),
            target_type=getattr(skill, 'target_type', 'single'),
            description=getattr(skill, 'description', ''),
            cooldown_remaining=getattr(skill, 'cooldown_remaining', 0)
        )
    
    @staticmethod
    def _convert_item(item: Any) -> ItemInfo:
        """아이템을 ItemInfo로 변환"""
        return ItemInfo(
            id=getattr(item, 'id', getattr(item, 'item_id', 'unknown')),
            name=getattr(item, 'name', 'Unknown'),
            quantity=getattr(item, 'quantity', 1),
            effect=getattr(item, 'effect', getattr(item, 'description', ''))
        )


# =============================================================================
# 편의 함수
# =============================================================================

def create_llm_bot(
    name: str,
    job_id: str = "warrior",
    model: str = "qwen3:4b",
    style: PlayStyle = PlayStyle.BALANCED,
    enable_thinking: bool = True,
    enable_commentary: bool = True,
    async_mode: bool = True
) -> LLMPlayerBot:
    """
    간편하게 LLM 봇 생성
    
    Args:
        name: 봇 이름
        job_id: 직업 ID (warrior, knight, archmage, cleric 등)
        model: Ollama 모델명 (qwen3:4b 추천)
        style: 플레이 스타일
        enable_thinking: Qwen3 thinking 모드 활성화
        enable_commentary: 실시간 해설 활성화
        async_mode: 비동기 모드 (게임 프레임 드롭 방지)
        
    Returns:
        LLMPlayerBot 인스턴스
    """
    import uuid
    config = LLMConfig(
        model=model,
        play_style=style,
        enable_thinking=enable_thinking,
        enable_commentary=enable_commentary,
        async_mode=async_mode
    )
    return LLMPlayerBot(
        bot_id=str(uuid.uuid4()),
        bot_name=name,
        job_id=job_id,
        config=config
    )


def create_party_bots(
    party_config: List[Dict[str, str]],
    model: str = "qwen3:4b",
    style: PlayStyle = PlayStyle.BALANCED
) -> List[LLMPlayerBot]:
    """
    파티 전체 봇 생성
    
    Args:
        party_config: [{"name": "이름", "job": "직업ID"}, ...]
        model: Ollama 모델명
        style: 플레이 스타일
        
    Returns:
        LLMPlayerBot 리스트
    
    Example:
        >>> bots = create_party_bots([
        ...     {"name": "탱커봇", "job": "knight"},
        ...     {"name": "힐러봇", "job": "cleric"},
        ...     {"name": "딜러봇1", "job": "archmage"},
        ...     {"name": "딜러봇2", "job": "assassin"},
        ... ])
    """
    bots = []
    for member in party_config:
        bot = create_llm_bot(
            name=member.get("name", "Bot"),
            job_id=member.get("job", "warrior"),
            model=model,
            style=style
        )
        bots.append(bot)
    return bots


async def test_ollama_connection(base_url: str = "http://localhost:11434") -> bool:
    """Ollama 연결 테스트 (비동기)"""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{base_url}/api/tags")
            if response.status_code == 200:
                models = response.json().get("models", [])
                logger.info(f"Ollama 연결 성공! 사용 가능한 모델: {[m['name'] for m in models]}")
                return True
    except Exception as e:
        logger.error(f"Ollama 연결 실패: {e}")
    return False


def test_ollama_connection_sync(base_url: str = "http://localhost:11434") -> bool:
    """Ollama 연결 테스트 (동기)"""
    try:
        import httpx
        with httpx.Client(timeout=5.0) as client:
            response = client.get(f"{base_url}/api/tags")
            if response.status_code == 200:
                models = response.json().get("models", [])
                logger.info(f"Ollama 연결 성공! 사용 가능한 모델: {[m['name'] for m in models]}")
                return True
    except Exception as e:
        logger.error(f"Ollama 연결 실패: {e}")
    return False


def get_available_jobs(include_default: bool = False) -> List[str]:
    """
    사용 가능한 직업 목록 반환
    
    Args:
        include_default: 'default' 폴백 직업 포함 여부
        
    Returns:
        34개 직업 목록 (default 제외 시)
    """
    jobs = list(JOB_DATABASE.keys())
    if not include_default and "default" in jobs:
        jobs.remove("default")
    return jobs


def get_job_info(job_id: str) -> Dict[str, Any]:
    """직업 정보 반환"""
    return JOB_DATABASE.get(job_id, JOB_DATABASE.get("default", {}))


# =============================================================================
# 게임 통합 함수
# =============================================================================

def get_bot_action_for_combat(
    bot: LLMPlayerBot,
    combat_manager: Any,
    current_character: Any,
    inventory: Any = None
) -> BotAction:
    """
    CombatManager에서 봇 행동 결정 (게임 통합용)
    
    Args:
        bot: LLMPlayerBot 인스턴스
        combat_manager: CombatManager 인스턴스
        current_character: 현재 행동할 캐릭터
        inventory: 인벤토리 (선택)
        
    Returns:
        BotAction
        
    Example:
        >>> from src.multiplayer.llm_player_bot import create_llm_bot, get_bot_action_for_combat
        >>> bot = create_llm_bot("AI전사", "warrior")
        >>> action = get_bot_action_for_combat(bot, combat_manager, current_char)
        >>> if action.action_type == ActionType.SKILL:
        ...     combat_manager.execute_skill(current_char, action.skill_id, target)
    """
    # 게임 상태를 CombatState로 변환
    combat_state = GameStateConverter.from_combat_manager(
        combat_manager,
        current_character,
        inventory
    )
    
    # 봇이 행동 결정
    action = bot.decide_combat_action(combat_state)
    
    return action


def execute_bot_action(
    combat_manager: Any,
    actor: Any,
    action: BotAction,
    inventory: Any = None
) -> Dict[str, Any]:
    """
    봇 행동을 CombatManager에서 실행
    
    Args:
        combat_manager: CombatManager 인스턴스
        actor: 행동할 캐릭터
        action: BotAction
        inventory: 인벤토리 (아이템 사용 시)
        
    Returns:
        실행 결과 딕셔너리
    """
    # 타겟 찾기
    target = None
    if action.target_name:
        # 아군에서 찾기
        for ally in combat_manager.allies:
            if getattr(ally, 'name', '') == action.target_name:
                target = ally
                break
        # 적에서 찾기
        if not target:
            for enemy in combat_manager.enemies:
                if getattr(enemy, 'name', '') == action.target_name:
                    target = enemy
                    break
    
    # 타겟이 없으면 기본 타겟 선택
    if not target:
        if action.action_type in [ActionType.HP_ATTACK, ActionType.BRV_ATTACK]:
            # 적 중 살아있는 첫 번째
            for enemy in combat_manager.enemies:
                if getattr(enemy, 'is_alive', False):
                    target = enemy
                    break
        elif action.action_type == ActionType.ITEM:
            target = actor  # 아이템은 자신에게
    
    # 행동 실행
    result = {"action": action.action_type.value, "success": False}
    
    try:
        if action.action_type == ActionType.BRV_ATTACK:
            result = combat_manager.execute_action(actor, "brv_attack", target=target)
            
        elif action.action_type == ActionType.HP_ATTACK:
            result = combat_manager.execute_action(actor, "hp_attack", target=target)
            
        elif action.action_type == ActionType.SKILL:
            # 스킬 찾기
            skill = None
            if hasattr(actor, 'skills'):
                for s in actor.skills:
                    if getattr(s, 'skill_id', getattr(s, 'id', '')) == action.skill_id:
                        skill = s
                        break
            if skill:
                result = combat_manager.execute_action(actor, "skill", target=target, skill=skill)
            else:
                result = {"action": "skill", "success": False, "error": f"스킬 없음: {action.skill_id}"}
                
        elif action.action_type == ActionType.ITEM:
            if inventory and action.item_id:
                # 아이템 찾기
                item = None
                item_index = None
                for idx, inv_item in enumerate(inventory.get_usable_items()):
                    if getattr(inv_item, 'id', getattr(inv_item, 'item_id', '')) == action.item_id:
                        item = inv_item
                        item_index = idx
                        break
                if item:
                    result = combat_manager.execute_action(actor, "item", target=target, item=item, item_index=item_index)
                else:
                    result = {"action": "item", "success": False, "error": f"아이템 없음: {action.item_id}"}
            else:
                result = {"action": "item", "success": False, "error": "인벤토리 없음"}
                
        elif action.action_type == ActionType.DEFEND:
            result = combat_manager.execute_action(actor, "defend")
            
        elif action.action_type == ActionType.FLEE:
            result = combat_manager.execute_action(actor, "flee")
            
        result["success"] = True
        
    except Exception as e:
        logger.error(f"봇 행동 실행 오류: {e}")
        result["error"] = str(e)
    
    return result


# =============================================================================
# 자동 플레이 AI (탐험 + 전투 + 파티 구성)
# =============================================================================

class AutoPlayAI:
    """
    완전 자동 플레이 AI
    
    - 파티 구성 추천/선택
    - 던전 탐험 (맵 이동)
    - 전투 자동 진행
    - 특성 선택 추천
    """
    
    def __init__(self, config: Optional[LLMConfig] = None):
        self.config = config or LLMConfig()
        self.client = OllamaClientSync(self.config)
        self.combat_bots: Dict[str, LLMPlayerBot] = {}
        self.logger = get_logger("auto_play_ai")
        
    def recommend_party(self, available_jobs: List[str], num_members: int = 4) -> List[PartySetupChoice]:
        """파티 구성 추천"""
        job_info_text = ""
        for job in available_jobs[:12]:
            info = JOB_DATABASE.get(job, {})
            job_info_text += f"- {job}: {info.get('gimmick', '기본')}\n"
        
        prompt = f"""RPG 4인 파티 구성. 역할 균형 필요 (탱커/힐러/딜러).

직업 목록:
{job_info_text}
JSON: [{{"job":"ID","name":"이름","role":"역할"}}]"""

        try:
            response = self.client.generate(prompt, "파티 구성 전문가")
            import json
            import re
            json_match = re.search(r'\[.*\]', response, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
                return [
                    PartySetupChoice(
                        job_id=item.get("job", "warrior"),
                        character_name=item.get("name", f"영웅{i+1}"),
                        reasoning=item.get("role", "")
                    )
                    for i, item in enumerate(data[:num_members])
                ]
        except Exception as e:
            self.logger.warning(f"파티 추천 실패: {e}")
        
        # 폴백: 기본 파티
        return [
            PartySetupChoice("knight", "탱커", reasoning="탱커"),
            PartySetupChoice("cleric", "힐러", reasoning="힐러"),
            PartySetupChoice("archmage", "마법사", reasoning="마법딜러"),
            PartySetupChoice("warrior", "전사", reasoning="물리딜러"),
        ][:num_members]
    
    def recommend_traits(self, job_id: str, available_traits: List[Dict], max_traits: int = 3) -> List[str]:
        """특성 추천"""
        job_info = JOB_DATABASE.get(job_id, {})
        
        traits_text = "\n".join([
            f"- {t.get('id')}: {t.get('name', '')} - {t.get('description', '')[:50]}"
            for t in available_traits[:10]
        ])
        
        prompt = f"""직업: {job_info.get('name', job_id)} (기믹: {job_info.get('gimmick', '없음')})

특성 목록:
{traits_text}

최적 특성 {max_traits}개 선택. JSON: ["id1", "id2"]"""

        try:
            response = self.client.generate(prompt, "특성 전문가")
            import json
            import re
            json_match = re.search(r'\[.*\]', response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())[:max_traits]
        except:
            pass
        
        return [t.get("id") for t in available_traits[:max_traits] if t.get("id")]
    
    def decide_exploration_action(self, state: ExplorationState) -> ExplorationAction:
        """탐험 행동 결정 (규칙 기반 - 빠름)"""
        import random
        
        # 1. HP 낮으면 회복
        if state.party_hp_percent < 30:
            if state.has_healing_point:
                return ExplorationAction("rest", reasoning="HP 낮음, 회복")
            return ExplorationAction("use_item", target="potion", reasoning="HP 위험")
        
        # 2. 보물 수집
        if state.treasure_positions:
            tx, ty = state.treasure_positions[0]
            px, py = state.current_position
            dx = 1 if tx > px else (-1 if tx < px else 0)
            dy = 1 if ty > py else (-1 if ty < py else 0)
            return ExplorationAction("move", direction=(dx, dy), reasoning="보물 수집")
        
        # 3. 적 처리
        if state.nearby_enemies:
            if state.party_hp_percent > 50:
                return ExplorationAction("fight", reasoning="적 발견, 전투")
            return ExplorationAction("flee", reasoning="HP 낮음, 회피")
        
        # 4. 계단 이동
        if state.stairs_down_position and state.discovered_rooms >= state.total_rooms * 0.7:
            sx, sy = state.stairs_down_position
            px, py = state.current_position
            dx = 1 if sx > px else (-1 if sx < px else 0)
            dy = 1 if sy > py else (-1 if sy < py else 0)
            return ExplorationAction("move", direction=(dx, dy), reasoning="다음 층")
        
        # 5. 미탐험 지역
        if state.unexplored_directions:
            return ExplorationAction("move", direction=state.unexplored_directions[0], reasoning="탐색")
        
        # 6. 랜덤 이동
        return ExplorationAction("move", direction=random.choice([(0,1),(0,-1),(1,0),(-1,0)]), reasoning="탐색 계속")
    
    def create_combat_bot(self, character: Any) -> LLMPlayerBot:
        """캐릭터용 전투 봇"""
        name = getattr(character, 'name', 'Unknown')
        if name not in self.combat_bots:
            job = getattr(character, 'job_id', 'warrior')
            self.combat_bots[name] = create_llm_bot(name, job, self.config.model, self.config.play_style)
        return self.combat_bots[name]
    
    def decide_combat_action(self, combat_manager: Any, current_char: Any, inventory: Any = None) -> BotAction:
        """전투 행동 결정"""
        bot = self.create_combat_bot(current_char)
        return get_bot_action_for_combat(bot, combat_manager, current_char, inventory)
    
    def shutdown(self):
        """모든 봇 종료"""
        for bot in self.combat_bots.values():
            bot.shutdown()
        self.combat_bots.clear()


def create_auto_play_ai(model: str = "qwen3:0.6b", style: PlayStyle = PlayStyle.BALANCED) -> AutoPlayAI:
    """자동 플레이 AI 생성"""
    return AutoPlayAI(LLMConfig(model=model, play_style=style))
