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
    model: str = "qwen3:1.7b"  # 사용할 모델 (추천: qwen3:1.7b 가벼움, qwen3:4b 똑똑함)
    temperature: float = 0.3  # 낮을수록 일관된 결정
    timeout: float = 60.0  # 타임아웃 (초)
    max_tokens: int = 1024  # 최대 출력 토큰
    context_length: int = 8192  # 컨텍스트 길이 (8K 권장)
    num_gpu: int = 20  # GPU 레이어 수 (낮을수록 조용함, 0=CPU만)
    retry_count: int = 3  # 재시도 횟수
    enable_thinking: bool = False  # Qwen3 thinking 모드 (비활성화 권장)
    play_style: PlayStyle = PlayStyle.BALANCED  # 플레이 스타일
    enable_commentary: bool = True  # 실시간 해설 활성화
    async_mode: bool = True  # 비동기 모드


# =============================================================================
# 게임 상태 직렬화
# =============================================================================

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


@dataclass
class ExplorationAction:
    """탐험 행동"""
    action_type: str  # "move", "interact", "rest", "use_item"
    direction: Optional[Tuple[int, int]] = None  # 이동 방향
    target: Optional[str] = None  # 상호작용 대상
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

SYSTEM_PROMPT_BASE = """당신은 Dawn of Stellar 게임의 고급 플레이어입니다.
ATB + BRV 전투 시스템을 완벽히 이해하고 최적의 전략을 구사합니다.

## 핵심 전투 규칙
1. **BRV (브레이브)**: BRV 공격으로 적 BRV를 깎고 내 BRV를 쌓음
2. **HP 공격**: 쌓은 BRV만큼 적 HP에 피해, 공격 후 BRV는 0으로 초기화
3. **BREAK**: 적 BRV가 0이 되면 BREAK 상태, 이때 HP 공격하면 보너스 데미지
4. **ATB**: 게이지가 100%가 되면 행동 가능

## 전략 우선순위
1. 위험 상황 대응 (HP 20% 이하면 회복 우선)
2. BREAK 기회 포착 (적 BRV 낮으면 BRV 공격으로 BREAK)
3. BREAK 상태 적에게 HP 공격
4. BRV가 충분히 쌓였으면 HP 공격
5. 직업 기믹 최적 활용
6. 아이템/스킬 적절히 사용
"""

# 플레이 스타일별 추가 프롬프트
STYLE_PROMPTS = {
    PlayStyle.AGGRESSIVE: """
## 🔥 플레이 스타일: 공격적
- HP 공격을 적극적으로 사용하여 빠른 처치
- 리스크를 감수하더라도 높은 딜 우선
- BREAK 보너스를 최대한 활용
- 회복은 HP 15% 이하에서만""",

    PlayStyle.DEFENSIVE: """
## 🛡️ 플레이 스타일: 방어적
- 파티 생존을 최우선으로
- HP 50% 이하면 즉시 회복
- 탱커가 도발로 적을 견제
- 버프/디버프로 안정적 전투""",

    PlayStyle.BALANCED: """
## ⚖️ 플레이 스타일: 균형
- 상황에 따라 유연하게 대응
- 공격과 방어의 적절한 밸런스
- 파티 전체 시너지 고려""",

    PlayStyle.SPEEDRUN: """
## ⚡ 플레이 스타일: 스피드런
- 가장 빠른 클리어 방법 선택
- 잡몹은 전체 공격으로 빠르게 처리
- 보스전은 버스트 데미지 집중
- 불필요한 행동 최소화""",

    PlayStyle.RESOURCE_SAVER: """
## 💎 플레이 스타일: 자원 절약
- MP 소모 스킬은 보스전에만 사용
- 아이템은 최대한 아끼기
- 일반 공격으로 자원 관리
- 회복은 전투 후 회복 포인트에서""",
}

RESPONSE_FORMAT = """
## 응답 형식 (JSON)
반드시 다음 형식으로만 응답하세요:
```json
{
  "action": "brv_attack" | "hp_attack" | "skill" | "item" | "defend" | "flee",
  "target": "대상 이름 (적 또는 아군)",
  "skill_id": "스킬 ID (skill 선택 시)",
  "item_id": "아이템 ID (item 선택 시)",
  "reasoning": "판단 이유",
  "commentary": "플레이어에게 보여줄 실시간 해설 (선택)"
}
```
"""

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
    """플레이 스타일에 맞는 시스템 프롬프트 생성"""
    prompt = SYSTEM_PROMPT_BASE
    prompt += STYLE_PROMPTS.get(style, STYLE_PROMPTS[PlayStyle.BALANCED])
    prompt += RESPONSE_FORMAT
    
    if enable_commentary:
        prompt += "\n\n💬 commentary 필드에 짧은 해설을 추가해주세요!"
    
    # Qwen3 thinking 모드 제어
    if not enable_thinking:
        prompt += "\n\n/no_think"  # Qwen3 thinking 모드 비활성화
    
    return prompt


# 하위 호환성을 위한 기본 프롬프트
SYSTEM_PROMPT = get_system_prompt(PlayStyle.BALANCED)


def create_combat_prompt(state: CombatState, job_info: Dict[str, Any]) -> str:
    """전투 상황 프롬프트 생성"""
    
    # 아군 상태
    allies_text = ""
    for ally in state.allies:
        hp_percent = (ally.hp / ally.max_hp * 100) if ally.max_hp > 0 else 0
        status = "💀사망" if not ally.is_alive else ("💥BREAK" if ally.is_broken else "정상")
        gimmick_text = f", {ally.gimmick_name}: {ally.gimmick_value}" if ally.gimmick_name else ""
        allies_text += f"- {ally.name} ({ally.job}): HP {ally.hp}/{ally.max_hp} ({hp_percent:.0f}%), MP {ally.mp}/{ally.max_mp}, BRV {ally.brv}/{ally.max_brv}, ATB {ally.atb_percent:.0f}%, 상태: {status}{gimmick_text}\n"
        if ally.status_effects:
            allies_text += f"  상태이상: {', '.join(ally.status_effects)}\n"
    
    # 적 상태
    enemies_text = ""
    for enemy in state.enemies:
        hp_percent = (enemy.hp / enemy.max_hp * 100) if enemy.max_hp > 0 else 0
        status = "💀사망" if not enemy.is_alive else ("💥BREAK" if enemy.is_broken else "정상")
        enemies_text += f"- {enemy.name}: HP {enemy.hp}/{enemy.max_hp} ({hp_percent:.0f}%), BRV {enemy.brv}/{enemy.max_brv}, 상태: {status}\n"
        if enemy.status_effects:
            enemies_text += f"  상태이상: {', '.join(enemy.status_effects)}\n"
    
    # 스킬 목록
    skills_text = ""
    for skill in state.available_skills:
        cd_text = f" (쿨다운: {skill.cooldown_remaining}턴)" if skill.cooldown_remaining > 0 else ""
        skills_text += f"- {skill.id}: {skill.name} (MP {skill.mp_cost}, {skill.skill_type}, {skill.target_type}){cd_text}\n"
    
    # 아이템 목록
    items_text = ""
    for item in state.available_items:
        items_text += f"- {item.id}: {item.name} x{item.quantity} - {item.effect}\n"
    
    # 직업 기믹 팁
    job_tips = ""
    if job_info:
        job_tips = f"\n## 현재 직업 기믹 ({job_info.get('name', '?')})\n"
        job_tips += f"- 기믹: {job_info.get('gimmick', '없음')} - {job_info.get('gimmick_desc', '')}\n"
        tips = job_info.get('tips', [])
        if tips:
            job_tips += "- 팁:\n"
            for tip in tips[:3]:  # 상위 3개만
                job_tips += f"  * {tip}\n"
    
    prompt = f"""## 현재 전투 상황 (턴 {state.turn_count})
현재 행동할 캐릭터: **{state.current_actor}**

### 아군 파티
{allies_text}
### 적
{enemies_text}
### 사용 가능한 스킬
{skills_text if skills_text else "없음"}
### 보유 아이템
{items_text if items_text else "없음"}
{job_tips}
## 최적의 행동을 JSON으로 선택하세요:"""
    
    return prompt


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
            # 프롬프트 생성
            prompt = create_combat_prompt(combat_state, self.job_info)
            
            # 🧠 기억된 적 정보 추가
            enemy_names = [e.name for e in combat_state.enemies if e.is_alive]
            memory_context = self.get_memory_context(enemy_names)
            if memory_context:
                prompt = memory_context + "\n" + prompt
            
            # 👥 파티 전략 컨텍스트 추가
            if self.current_strategy:
                strategy_text = f"\n## 🎯 현재 파티 전략\n"
                strategy_text += f"- 집중 타겟: {self.current_strategy.focus_target}\n"
                if self.current_strategy.emergency_plan:
                    strategy_text += f"- 위기 대응: {self.current_strategy.emergency_plan}\n"
                prompt = strategy_text + prompt
            
            # 히스토리 추가
            if self.combat_history:
                history_text = "\n## 📜 최근 행동 기록\n" + "\n".join(self.combat_history[-3:])
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
        
        return CombatState(
            turn_count=combat_manager.turn_count,
            current_actor=getattr(current_character, 'name', 'Unknown'),
            allies=allies,
            enemies=enemies,
            available_skills=skills,
            available_items=items,
            can_flee=True,
            environment=""
        )
    
    @staticmethod
    def _convert_combatant(char: Any) -> CombatantState:
        """캐릭터를 CombatantState로 변환"""
        # 기믹 정보 추출
        gimmick_value = 0
        gimmick_name = ""
        if hasattr(char, 'gimmick_manager') and char.gimmick_manager:
            gimmick = char.gimmick_manager
            gimmick_name = getattr(gimmick, 'gimmick_name', '')
            gimmick_value = getattr(gimmick, 'current_value', 0)
        
        # 상태이상 추출
        status_effects = []
        if hasattr(char, 'status_effects'):
            for effect in char.status_effects:
                status_effects.append(getattr(effect, 'name', str(effect)))
        
        return CombatantState(
            name=getattr(char, 'name', 'Unknown'),
            job=getattr(char, 'job_name', getattr(char, 'character_class', 'Unknown')),
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
            gimmick_name=gimmick_name
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
