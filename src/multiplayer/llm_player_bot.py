"""
LLM 기반 고급 플레이어 봇
Dawn of Stellar

Ollama를 사용하여 로컬 LLM으로 고급 플레이어처럼 게임을 플레이하는 AI 봇입니다.
모든 게임 기능(전투, 스킬, 아이템, 요리, 직업 기믹)을 완벽히 활용합니다.
"""

import os
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
from pathlib import Path

from src.core.logger import get_logger
from src.tutorial.tutorial_bot import JOB_DATABASE, COOKING_DATABASE, STATUS_EFFECTS

logger = get_logger("llm_player_bot")

# .env 파일에서 API 키 자동 로드
def _load_dotenv():
    """프로젝트 루트의 .env 파일에서 환경변수 로드"""
    # 프로젝트 루트 탐색 (src/multiplayer/ 기준 2단계 위)
    env_path = Path(__file__).resolve().parent.parent.parent / ".env"
    if not env_path.exists():
        return
    try:
        with open(env_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    key, _, value = line.partition("=")
                    key = key.strip()
                    value = value.strip()
                    # 이미 설정된 환경변수는 덮어쓰지 않음
                    if key and value and not os.environ.get(key):
                        os.environ[key] = value
                        logger.info(f".env 로드: {key}=***")
    except Exception as e:
        logger.warning(f".env 파일 로드 실패: {e}")

_load_dotenv()


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
    base_url: str = "http://localhost:11434"  # Ollama 로컬 주소
    model: str = "gemini-3-flash-preview"  # Cloud 모델
    use_cloud: bool = True  # True: Ollama Cloud (OLLAMA_API_KEY 필요), False: 로컬
    temperature: float = 0.3  # 낮을수록 일관된 결정
    timeout: float = 60.0  # 타임아웃 (Cloud는 네트워크 지연 고려)
    max_tokens: int = 2048  # 응답 토큰 (간결하게)
    context_length: int = 16384  # 컨텍스트 길이
    num_gpu: int = 99  # GPU (Cloud에서는 무시됨)
    retry_count: int = 3  # 재시도 횟수
    enable_thinking: bool = False  # Qwen3 thinking 모드
    play_style: PlayStyle = PlayStyle.BALANCED  # 플레이 스타일
    enable_commentary: bool = True  # 실시간 해설 활성화
    async_mode: bool = True  # 비동기 모드
    detailed_prompt: bool = True  # True=상세 프롬프트 (느리지만 정확), False=간소화 (빠름)
    boss_mode: bool = False  # 보스전용 상세 분석 모드
    provider: str = "ollama"  # "openai" or "ollama"


# =============================================================================
# 시스템 프롬프트
# =============================================================================

EXPLORATION_SYSTEM_PROMPT = """당신은 Dawn of Stellar 게임의 탐험 AI입니다.
던전을 효율적으로 탐험하고 자원을 수집합니다.

## 우선순위
1. 생존: HP 30% 미만이면 회복 아이템 사용 또는 안전 지대로 이동
2. 위험 회피: 데미지 타일(용암, 독가스 등) 우회, 불가피시 회복 준비
3. 파밍: 보물상자, 아이템, 오브젝트 수집
4. 탐험: 미탐험 지역 발견
5. 진행: 충분히 탐험 후 계단으로 이동

## 행동 유형
- move: 특정 위치로 이동
- interact: 오브젝트 상호작용 (상자 열기, NPC 대화)
- use_item: 아이템 사용 (회복 등)
- fight: 적과 전투
- flee: 도망
- pickup: 아이템 줍기
- open_chest: 보물상자 열기

JSON 형식으로 응답하세요."""

TOWN_SYSTEM_PROMPT = """당신은 Dawn of Stellar 게임의 마을 관리 AI입니다.
마을에서 효율적으로 준비하고 자원을 관리합니다.

## 우선순위
1. 회복: HP/MP가 낮으면 휴식
2. 구매: 회복 아이템, 필요한 장비 구매
3. 정비: 장비 수리, 인벤토리 정리
4. 강화: 여유가 있으면 시설 업그레이드
5. 출발: 준비 완료 후 던전 출발

## 행동 유형
- buy: 아이템/장비 구매
- sell: 아이템 판매
- repair: 장비 수리
- cook: 요리 제작
- craft: 장비 제작
- rest: 휴식 (HP/MP 회복)
- upgrade: 시설 업그레이드
- storage: 창고 이용
- depart: 던전 출발

JSON 형식으로 응답하세요."""


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
    # 화면 텍스트 (실제 플레이어가 보는 화면)
    screen_text: str = ""  # 콘솔 화면 텍스트


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
    
    # 환경 타일 정보 (LLM 인식용)
    hazard_tiles: List[Dict[str, Any]] = field(default_factory=list)  # 위험 타일 [{pos: (x,y), type: "lava", damage: 10}]
    safe_tiles: List[Tuple[int, int]] = field(default_factory=list)  # 안전한 타일
    objects: List[Dict[str, Any]] = field(default_factory=list)  # 오브젝트 [{pos: (x,y), type: "chest", interactable: True}]
    
    # 인벤토리 상태 (회복 아이템 사용 판단용)
    healing_items: List[Dict[str, Any]] = field(default_factory=list)  # [{name: "포션", heal: 50, count: 3}]
    gold: int = 0  # 현재 골드
    # 화면 텍스트 (실제 플레이어가 보는 화면)
    screen_text: str = ""  # 콘솔 화면 텍스트


@dataclass
class ExplorationAction:
    """탐험 행동"""
    action_type: str  # "move", "interact", "rest", "use_item", "flee", "fight", "pickup", "open_chest"
    direction: Optional[Tuple[int, int]] = None  # 이동 방향
    target: Optional[str] = None  # 상호작용 대상
    target_position: Optional[Tuple[int, int]] = None  # 목표 위치 (A*용)
    item_to_use: Optional[str] = None  # 사용할 아이템 (회복 등)
    avoid_hazards: bool = True  # 위험 타일 회피 여부
    reasoning: str = ""


@dataclass
class PartySetupChoice:
    """파티 구성 선택"""
    job_id: str
    character_name: str
    traits: List[str] = field(default_factory=list)  # 선택할 특성 ID
    reasoning: str = ""


@dataclass
class TownState:
    """마을 상태"""
    # 파티 상태
    party_hp_percent: float  # 파티 평균 HP%
    party_mp_percent: float  # 파티 평균 MP%
    gold: int  # 현재 골드
    
    # 인벤토리 상태
    inventory_items: List[Dict[str, Any]] = field(default_factory=list)  # 보유 아이템
    sellable_items: List[str] = field(default_factory=list)  # 판매 가능 아이템
    inventory_weight: int = 0  # 현재 무게
    max_weight: int = 20  # 최대 무게
    
    # 시설 상태
    facilities: Dict[str, int] = field(default_factory=dict)  # 시설별 레벨
    
    # 상점 상태
    shop_items: List[Dict[str, Any]] = field(default_factory=list)  # 구매 가능 아이템
    
    # 요리 상태
    available_recipes: List[str] = field(default_factory=list)  # 제작 가능한 요리
    cooking_ingredients: List[str] = field(default_factory=list)  # 보유 재료
    
    # 장비 상태
    damaged_equipment: List[str] = field(default_factory=list)  # 수리 필요한 장비
    craftable_equipment: List[str] = field(default_factory=list)  # 제작 가능한 장비
    
    # 던전 준비 상태
    ready_for_dungeon: bool = False  # 던전 출발 준비 완료


@dataclass
class TownAction:
    """마을 행동"""
    action_type: str  # "buy", "sell", "repair", "cook", "craft", "rest", "upgrade", "storage", "depart"
    target: Optional[str] = None  # 대상 (아이템 ID, 시설 ID 등)
    quantity: int = 1  # 수량
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
6. **스킬은 언제든지 사용 가능! 상황에 맞춰 적극 활용하세요.**

## 중요: 직업별 역할 수행!
- 탱커: 도발, 방어 스킬로 파티 보호
- 힐러: 회복 스킬 우선! HP 70% 이하면 힐
- 버퍼: 버프 스킬 우선! 공격/방어 버프 유지
- 디버퍼: 디버프 스킬로 적 약화
- 딜러: 공격 스킬로 데미지

JSON 응답 형식:
{"action":"brv_attack|hp_attack|skill|item|defend","target":"적_이름","skill_id":"스킬ID","reasoning":"이유"}
"""

# 직업별 역할 가이드 (34개 전체) - 기믹 메커니즘 + 실전 운용법
JOB_ROLE_GUIDE = {
    # === 물리 딜러 ===
    "warrior": "⚔️ 전사 [6단계 스탠스]: 스탠스에 따라 능력치 변화. balanced_stance=기본, attack_stance=공격↑방어↓, defensive_stance=방어↑. 상황 따라 스탠스 전환 후 BRV쌓고 HP공격!",
    "archer": "🏹 궁수 [지원사격]: mark_*로 적에 화살 설치(최대3개)→BRV/HP공격 시 설치된 화살 자동 발사! 원소화살(fire/ice/poison)로 속성 부여. 화살 쌓고 터뜨리기!",
    "assassin": "🗡️ 암살자 [은신-노출]: vanish로 은신→은신 중 backstab/assassinate 치명타 보너스! 공격하면 노출됨. 은신→강타→재은신 반복!",
    "berserker": "💢 버서커 [광기 역치]: HP 낮아질수록 광기↑, 광기 높으면 데미지↑↑ 단 받는피해도↑. self_harm으로 의도적 광기 축적, blood_rage로 폭발! 위험하면 healing_roar!",
    "breaker": "💥 브레이커 [파괴력 축적]: BRV 공격할수록 파괴력 게이지↑, 파괴력 높으면 BREAK 보너스↑↑. crush/break_hit으로 쌓고 mega_crush로 터뜨려! BRV공격 많이!",
    "gladiator": "🗡️ 검투사 [군중의 환호]: 화려한 스킬(spectacular/risky_stunt)로 환호↑, 환호 높으면 버프! 위험한 기술 성공 시 대박. taunt로 어그로, glory_strike로 마무리!",
    "monk": "👊 몽크 [음양 기 흐름]: yin_strike=음기↑, yang_strike=양기↑. 음양 균형 맞추면 버프! 한쪽 극대화(yin_extreme/yang_extreme)도 가능. 번갈아 치다가 taichi_flow!",
    "rogue": "🥷 로그 [절도와 회피]: steal로 적 아이템 훔치기, 훔친 아이템 use_item으로 사용! smoke로 회피율↑, ambush→vital_strike→backstab 콤보. 빠른 연타!",
    "samurai": "⚔️ 사무라이 [거합의 도]: clear_mind로 집중↑, 집중 높을수록 battojutsu/iaido 치명타↑. 집중 쌓고→발도술 한 방! true_battojutsu는 집중 전부 소모 초강력!",
    "sniper": "🎯 스나이퍼 [탄창 관리]: reload로 재장전, load_*로 특수탄 장전(penetrating/explosive). perfect_aim으로 정조준 후 headshot! 탄 관리하며 한 방 노리기!",
    "sword_saint": "⚔️ 검성 [검기]: 공격할수록 검기↑, 검기 높으면 스킬 데미지↑. kenkizan/ilseom으로 쌓고 kenki_hadou/bisect로 방출! 검기 꽉 차면 sword_storm!",
    
    # === 마법 딜러 ===
    "archmage": "🔮 대마법사 [원소 조합]: 3원소(불/얼음/번개) 번갈아 사용하면 조합 카운터↑. 카운터 3이면 elemental_surge 자동발동! 단일원소 연속은 비효율. 원소 돌려가며 사용!",
    "battle_mage": "⚔️🔮 배틀메이지 [룬 공명]: carve_rune으로 룬 새기고, 원소룬(fire/ice/lightning/earth)으로 속성 부여→rune_burst로 폭발! 룬 많이 쌓으면 elemental_fusion!",
    "spellblade": "⚔️✨ 스펠블레이드 [마력 부여]: fire/ice/lightning_infusion으로 무기에 속성 부여(지속)→magic_slash/elemental_slash 속성 데미지! 부여 후 물리 연타!",
    "necromancer": "💀 강령술사 [언데드 군단]: summon_*로 언데드 소환(skeleton/zombie/ghost)→언데드가 자동 공격. sacrifice_undead로 언데드 터뜨려 폭딜! legion_command로 전체 지휘!",
    "elementalist": "🌪️ 정령술사 [4대 정령]: summon_fire/water/wind/earth로 정령 소환→spirit_burst로 정령 폭발! 2정령 조합(fusion_firestorm/mudtrap/steam) 상황별 활용!",
    
    # === 탱커 ===
    "dark_knight": "🌑 암흑기사 [충전 시스템]: charge_strike로 충전↑, 충전 높으면 crushing_blow/execution 데미지↑↑. HP 소모 스킬 많으니 dark_regeneration으로 자힐! 충전→방출 반복!",
    "paladin": "🛡️ 팔라딘 [성스러운 힘]: 힐/보호 스킬 쓸수록 신성↑, 신성 높으면 holy스킬 강화. divine_shield로 파티 보호, holy_light로 자힐, blessing으로 버프!",
    "dimensionist": "🌀 차원술사 [차원 굴절]: refraction_strike로 받은 피해 일부 저장→refraction_release로 저장된 피해 반사! dimension_barrier로 방어, 맞으면서 반격!",
    "dragon_knight": "🐉 용기사 [용의 각인]: 화염 스킬로 적에 각인 새김(최대3개)→dragon_mark_strike로 각인 폭발! 각인 쌓고 터뜨리기! dragon_scales로 방어, dragon_storm 궁극기!",
    
    # === 힐러 ===
    "priest": "🙏 사제 [신성 권능]: 신성 스킬 사용 시 권능↑, 권능 높으면 힐량↑. holy_heal로 회복, divine_protection으로 보호막! 아군 HP 70% 이하면 힐 우선!",
    "cleric": "⛪ 클레릭 [신앙의 힘]: pray로 신앙↑→heal/greater_heal 강화! holy_barrier로 보호막, mass_heal 광역힐, resurrect 부활! 아군 HP 관리 최우선!",
    "druid": "🌿 드루이드 [자연의 변신]: bear_form=탱킹(체력↑), cat_form=딜링(공격↑), wolf_form=속도↑, eagle_form=회피↑. 상황 따라 변신! healing_forest 광역힐!",
    
    # === 버퍼/디버퍼 ===
    "bard": "🎵 바드 [악보 작곡]: 스킬마다 음표 추가(A공격/B버프/S서포트). 3음표=소나타, 4음표=협주곡, 5음표=교향곡! 특수조합: AAA=공격↑80%, BBB=버프2배, ABS=올스탯↑. 음표 조합 고려해서 스킬 선택!",
    "knight": "🛡️ 기사 [기사의 의무]: oath로 아군 지정→해당 아군 보호+버프. chivalry/devotion으로 파티 버프! iron_will로 도발, last_stand 위기시. 보호 대상 지정 후 버프!",
    "time_mage": "⏰ 시간마법사 [타임라인 균형]: slow/stop으로 적 지연, haste로 아군 가속. 시간 조작 많이 쓰면 균형 깨짐→balance로 복구! rewind 되감기, foresight 회피!",
    "hacker": "💻 해커 [멀티스레드]: run_*로 프로세스 실행(virus/backdoor/ddos/ransomware)→프로세스 많을수록 버프. terminate_all로 전부 종료하며 폭딜! 프로세스 쌓고 터뜨리기!",
    "shaman": "👁️ 샤먼 [저주 축적]: curse로 저주 스택↑, 스택 높을수록 DoT↑. plague로 전염, curse_burst로 폭발! curse_transfer로 아군→적 저주 전이. 저주 쌓고 터뜨리기!",
    
    # === 유틸리티/특수 ===
    "alchemist": "🧪 연금술사 [포션 조합]: gather로 재료 수집→heal/buff/mana_potion 조합! 재료 많으면 고급포션. acid_flask 공격, chain으로 연계 폭발! 재료 관리하며 적재적소 포션!",
    "engineer": "🔧 엔지니어 [열 관리]: 공격스킬 쓸수록 열↑, 열 높으면 오버히트! cooling_vent로 냉각. 열 적당할 때 overclock_mode 폭딜! shield_generator 방어, deploy_drone 지원!",
    "magician": "🎩 마술사 [트릭 덱]: card_slash로 카드 뽑기, 뽑은 카드로 효과 결정! ace_in_the_hole=강패, double_or_nothing=도박. 카드 조합(fatal_flush/full_house) 노리기!",
    "philosopher": "📚 철학자 [딜레마 선택]: choose_*로 딜레마 선택→선택에 따라 다른 효과! power=공격↑, wisdom=마법↑, sacrifice=HP소모 강화, survival=방어↑. 상황 따라 선택!",
    "pirate": "🏴‍☠️ 해적 [럼주와 보물]: 럼 마시면 버프+리스크, 보물 찾으면 랜덤 보상! 도박성 스킬 많음. 운 좋으면 대박, 나쁘면 쪽박. 리스크 감수하고 도박!",
    "vampire": "🧛 흡혈귀 [갈증 관리]: vampiric_bite/blood_drain으로 흡혈+갈증↑, 갈증 높으면 공격↑ 단 지속피해. thirst_surge로 갈증 폭발! blood_satiation으로 갈증 안정화. 갈증 조절하며 싸우기!",
}


# 플레이 스타일별 추가 프롬프트 (상황에 따라 동적으로 결정됨)
STYLE_PROMPTS = {
    PlayStyle.AGGRESSIVE: "공격적: 강력한 공격 스킬과 HP공격 우선, 리스크 감수. 높은 데미지 딜링 스킬 자주 사용!",
    PlayStyle.DEFENSIVE: "방어적: HP 50% 이하면 회복 스킬 우선, 버프/디버프 스킬로 보호. 안정성 중시.",
    PlayStyle.BALANCED: "균형: 상황에 맞춰 공격/회복/버프 스킬 적절히 사용. 전략적 판단.",
    PlayStyle.SPEEDRUN: "스피드: 높은 데미지 스킬로 빠른 처치. 회복은 필요할 때만.",
    PlayStyle.RESOURCE_SAVER: "절약: MP 관리하며 효율적인 스킬 사용. 자주 사용 가능한 저비용 스킬 선호.",
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
    
    # 살아있는 적 목록
    alive_enemies = [e for e in state.enemies if e.is_alive]
    first_enemy = alive_enemies[0].name if alive_enemies else "적"
    
    if not current:
        # allies가 비어있어도 적 목록은 제공
        if alive_enemies:
            enemy_names = ", ".join(e.name for e in alive_enemies)
            return f"적: {enemy_names}\n기본 타겟: {first_enemy}\nJSON: {{\"action\":\"brv_attack\",\"target\":\"{first_enemy}\",\"reasoning\":\"기본 공격\"}}"
        return f"{{\"action\":\"brv_attack\",\"target\":\"{first_enemy}\",\"reasoning\":\"기본 공격\"}}"
    
    # === 간소화 모드 (빠른 응답) ===
    if not detailed:
        # 직업 역할 가이드 가져오기
        job_key = current.job.lower().replace(" ", "_") if current.job else "warrior"
        role_guide = JOB_ROLE_GUIDE.get(job_key, "⚔️ 딜러! 공격 스킬 우선!")
        
        # 현재 캐릭터 (최대값 포함)
        hp_pct = int(current.hp / current.max_hp * 100) if current.max_hp > 0 else 0
        brv_pct = int(current.brv / current.max_brv * 100) if current.max_brv > 0 else 0
        me = f"{current.name}({current.job}):HP{hp_pct}% BRV{brv_pct}%({current.brv}/{current.max_brv})"
        if current.gimmick_name:
            me += f" {current.gimmick_name}:{current.gimmick_value}"

        # 적 상태 (전략적 정보 포함)
        enemies = []
        target_priorities = []  # (우선순위 점수, 적 이름, 이유)
        for idx, e in enumerate(state.enemies):
            if e.is_alive:
                e_hp = int(e.hp / e.max_hp * 100) if e.max_hp > 0 else 0
                e_brv = int(e.brv / e.max_brv * 100) if e.max_brv > 0 else 0
                
                # 타겟 우선순위 계산
                priority = 0
                reasons = []
                
                # BREAK 상태 = 최고 우선순위 (HP 공격 보너스)
                if e.is_broken:
                    priority += 100
                    reasons.append("BREAK!")
                
                # HP 낮은 적 = 높은 우선순위 (마무리 가능)
                if e_hp < 30:
                    priority += 50
                    reasons.append(f"HP{e_hp}%")
                elif e_hp < 50:
                    priority += 30
                    reasons.append(f"HP{e_hp}%")
                
                # BRV 낮은 적 = BREAK 노리기 좋음
                if e_brv < 30:
                    priority += 20
                    reasons.append(f"BRV낮음")
                
                # 디버프 상태인 적 = 우선 공격
                if e.debuffs:
                    priority += 15
                    reasons.append("디버프")
                
                target_priorities.append((priority, e.name, reasons))
                
                status = " 💥[BREAK!]" if e.is_broken else ""
                hp_warn = " ⚠️[HP낮음!]" if e_hp < 30 else ""
                brv_warn = " 🎯[BRV낮음]" if e_brv < 30 else ""
                debuff_mark = " 💀[디버프]" if e.debuffs else ""
                enemies.append(f"{idx+1}. {e.name}: HP {e_hp}% BRV {e_brv}%{hp_warn}{brv_warn}{status}{debuff_mark}")
        
        # 우선순위 정렬
        target_priorities.sort(reverse=True, key=lambda x: x[0])

        # 위험한 아군
        low_hp_allies = [a.name for a in state.allies if a.is_alive and a.hp < a.max_hp * 0.3]

        # 스킬 (더 많이, 각 줄로 표시)
        skills_lines = []
        for s in state.available_skills[:10]:  # 10개까지 표시 (이전: 5개)
            desc = f" - {s.description}" if s.description else ""
            skills_lines.append(f"  {s.id}({s.skill_type}, MP{s.mp_cost}){desc}")

        # 전략 추천 - 역할 기반!
        skill_recommendations = []
        
        # 역할 기반 추천 스킬 찾기
        buff_skills = [s for s in state.available_skills if 'buff' in s.skill_type.lower() or 'support' in s.skill_type.lower()]
        heal_skills = [s for s in state.available_skills if 'heal' in s.skill_type.lower() or 'recovery' in s.skill_type.lower()]
        attack_skills = [s for s in state.available_skills if 'attack' in s.skill_type.lower() or 'damage' in s.skill_type.lower() or 'brv' in s.skill_type.lower()]
        
        # 역할별 스킬 추천 (이름으로도 판단)
        for s in state.available_skills:
            name_lower = s.name.lower() if s.name else ""
            id_lower = s.id.lower() if s.id else ""
            desc_lower = s.description.lower() if s.description else ""
            
            if any(kw in name_lower or kw in id_lower or kw in desc_lower for kw in ['버프', 'buff', '강화', '증가', 'march', 'inspire', 'song']):
                if s not in buff_skills:
                    buff_skills.append(s)
            if any(kw in name_lower or kw in id_lower or kw in desc_lower for kw in ['힐', 'heal', '회복', '치유', 'cure', 'melody']):
                if s not in heal_skills:
                    heal_skills.append(s)
        
        # 직업 역할에 따른 추천 (34개 직업 기준)
        is_buffer = job_key in ['bard', 'knight', 'time_mage', 'engineer', 'shaman']
        is_healer = job_key in ['priest', 'cleric', 'druid', 'paladin']
        is_debuffer = job_key in ['hacker', 'necromancer', 'shaman']
        is_tank = job_key in ['paladin', 'dimensionist', 'knight', 'warrior']
        
        # 디버프 스킬 찾기
        debuff_skills = [s for s in state.available_skills 
                        if any(kw in (s.skill_type or '').lower() or kw in (s.id or '').lower() or kw in (s.description or '').lower()
                              for kw in ['debuff', '약화', '저주', 'curse', 'slow', 'blind', 'poison'])]
        
        if is_buffer and buff_skills:
            skill_recommendations.append(f"🎵 버퍼! → {buff_skills[0].id} 스킬 사용!")
        if is_healer and heal_skills:
            any_low_hp = any(a.hp < a.max_hp * 0.7 for a in state.allies if a.is_alive)
            if any_low_hp:
                skill_recommendations.append(f"💚 힐러! → {heal_skills[0].id} 스킬 사용!")
        if is_debuffer and debuff_skills:
            skill_recommendations.append(f"💀 디버퍼! → {debuff_skills[0].id} 스킬 사용!")
        
        # HP 상태
        if current.hp < current.max_hp * 0.3:
            skill_recommendations.append("⚠️ HP 위험!")
        
        # 적 상태
        alive_enemy_count = len([e for e in state.enemies if e.is_alive])
        low_hp_enemies = [e for e in state.enemies if e.is_alive and e.hp < e.max_hp * 0.3]
        broken_enemies = [e for e in state.enemies if e.is_alive and e.is_broken]
        
        if broken_enemies and not is_buffer and not is_healer:
            skill_recommendations.append(f"💥 {broken_enemies[0].name} BREAK! HP 공격!")
        if low_hp_enemies and not is_buffer:
            skill_recommendations.append(f"🎯 {low_hp_enemies[0].name} HP 낮음!")

        # 화면 텍스트 (실제 플레이어가 보는 화면)
        screen_section = ""
        if state.screen_text:
            # 화면 텍스트가 너무 길면 요약
            screen_lines = state.screen_text.split('\n')
            if len(screen_lines) > 20:
                screen_lines = screen_lines[:20] + ["... (화면 생략)"]
            screen_section = f"\n[현재 화면]\n{chr(10).join(screen_lines)}\n"

        # 전략적 타겟 추천 (우선순위 기반)
        target_recommendations = []
        if target_priorities:
            # 상위 3개 타겟 추천
            for i, (priority, name, reasons) in enumerate(target_priorities[:3]):
                if priority > 0:
                    reason_str = ", ".join(reasons) if reasons else "기본"
                    if i == 0:
                        target_recommendations.append(f"🎯 최우선 타겟: {name} ({reason_str})")
                    else:
                        target_recommendations.append(f"   대안 타겟: {name} ({reason_str})")
        
        # BREAK 적 강조
        broken_names = [e.name for e in state.enemies if e.is_alive and e.is_broken]
        if broken_names:
            target_recommendations.insert(0, f"💥 BREAK 상태! {', '.join(broken_names)}에게 HP 공격 강추!")
        
        # 기본 타겟 (최고 우선순위)
        best_target = target_priorities[0][1] if target_priorities else first_enemy
        
        prompt = f"""나:{me}
🎭 역할: {role_guide}

적 목록:
{chr(10).join(enemies)}

## 타겟 선택 가이드
{chr(10).join(target_recommendations) if target_recommendations else "🎯 상황에 맞는 타겟 선택!"}

{"⚠️ 위험한 아군: " + ','.join(low_hp_allies) + " → 힌 필요!" if low_hp_allies else ""}

📜 스킬:
{chr(10).join(skills_lines) if skills_lines else "  (스킬 없음)"}

{chr(10).join(skill_recommendations) if skill_recommendations else ""}

## 행동 결정 규칙 (반드시 따를 것!)
1. ⚠️ BREAK 상태 적이 있으면 → 무조건 hp_attack! (brv_attack 금지!)
2. 내 BRV가 높으면 → hp_attack
3. 적 BRV가 낮으면 → brv_attack으로 BREAK 유도
4. 아군 HP 낮으면 → 힐 스킬
5. HP 낮은 적 → 마무리!

JSON 응답 (target을 신중히 선택!):"""
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
    
    # 적 상태 (전략적 정보 포함)
    lines.append("\n### 적 (타겟 우선순위)")
    enemy_priorities = []
    for enemy in state.enemies:
        if not enemy.is_alive:
            continue
        hp_pct = int(enemy.hp / enemy.max_hp * 100)
        brv_pct = int(enemy.brv / enemy.max_brv * 100) if enemy.max_brv > 0 else 0
        
        # 우선순위 계산
        priority = 0
        tags = []
        if enemy.is_broken:
            priority += 100
            tags.append("💥BREAK")
        if hp_pct < 30:
            priority += 50
            tags.append("⚠️HP낮음")
        elif hp_pct < 50:
            priority += 30
        if brv_pct < 30:
            priority += 20
            tags.append("🎯BRV낮음")
        if enemy.debuffs:
            priority += 15
            tags.append("💀디버프")
        
        enemy_priorities.append((priority, enemy.name))
        
        status = "[BREAK!]" if enemy.is_broken else ""
        effects = f" ({', '.join(enemy.status_effects)})" if enemy.status_effects else ""
        tag_str = f" {' '.join(tags)}" if tags else ""
        lines.append(f"- {enemy.name}: HP{hp_pct}% BRV{brv_pct}% {status}{effects}{tag_str}")
    
    # 타겟 추천
    enemy_priorities.sort(reverse=True, key=lambda x: x[0])
    if enemy_priorities:
        best_target = enemy_priorities[0][1]
        lines.append(f"\n🎯 추천 타겟: {best_target}")
    
    # 스킬
    if state.available_skills:
        lines.append("\n### 스킬 (상황에 맞춰 적극 활용하세요!)")
        for skill in state.available_skills[:12]:  # 12개까지 표시 (이전: 6개)
            cd = f" (쿨{skill.cooldown_remaining})" if skill.cooldown_remaining > 0 else " ✓준비"
            desc = f" - {skill.description}" if skill.description else ""
            lines.append(f"- {skill.id}: {skill.name} [{skill.skill_type}] MP{skill.mp_cost}{cd}{desc}")

    # 아이템
    if state.available_items:
        lines.append("\n### 아이템")
        for item in state.available_items[:4]:
            lines.append(f"- {item.id}: {item.name} x{item.quantity}")

    # 전술 가이드
    lines.append("\n### 전술 가이드")
    low_ally_count = sum(1 for a in state.allies if a.is_alive and a.hp < a.max_hp * 0.4)
    broken_enemies = [e.name for e in state.enemies if e.is_alive and e.is_broken]
    low_hp_enemies = [e.name for e in state.enemies if e.is_alive and e.hp < e.max_hp * 0.3]

    if low_ally_count > 0:
        lines.append(f"- ⚠️ 아군 {low_ally_count}명이 위험합니다. 힐 스킬 사용!")
    if broken_enemies:
        lines.append(f"- 💥💥 {', '.join(broken_enemies)} BREAK 상태! → hp_attack 필수!! (brv_attack 절대 금지!)")
    if low_hp_enemies:
        lines.append(f"- 🎯 {', '.join(low_hp_enemies)} HP 낮음! 마무리 기회!")
    if current.brv > current.max_brv * 0.7:
        lines.append(f"- BRV가 충분합니다. HP 공격 추천!")
    if current.mp < current.max_mp * 0.3:
        lines.append(f"- MP가 부족합니다. 저코스트 스킬이나 물리 공격 고려!")

    lines.append("\n## 중요: 상황에 맞는 타겟 선택!")
    lines.append("행동 선택(JSON):")
    return "\n".join(lines)


# =============================================================================
# Ollama 클라이언트
# =============================================================================

class OllamaClient:
    """Ollama API 클라이언트"""
    
    def __init__(self, config: LLMConfig):
        self.config = config
        
        # Cloud 모드면 URL과 헤더 설정
        headers = {}
        if config.use_cloud:
            self.base_url = "https://ollama.com"
            api_key = os.environ.get('OLLAMA_API_KEY', '')
            if api_key:
                headers['Authorization'] = f'Bearer {api_key}'
            else:
                logger.warning("OLLAMA_API_KEY 환경변수가 설정되지 않음. Cloud 모드 실패 가능")
        else:
            self.base_url = config.base_url
        
        self.client = httpx.AsyncClient(timeout=config.timeout, headers=headers)
    
    async def generate(self, prompt: str, system_prompt: str = "") -> str:
        """텍스트 생성"""
        url = f"{self.base_url}/api/generate"
        
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
        url = f"{self.base_url}/api/chat"
        
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
        
        # Cloud 모드면 URL과 헤더 설정
        self.headers = {}
        if config.use_cloud:
            self.base_url = "https://ollama.com"
            api_key = os.environ.get('OLLAMA_API_KEY', '')
            if api_key:
                self.headers['Authorization'] = f'Bearer {api_key}'
        else:
            self.base_url = config.base_url
    
    def generate(self, prompt: str, system_prompt: str = "") -> str:
        """동기 텍스트 생성"""
        import httpx
        
        url = f"{self.base_url}/api/generate"
        
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
        
        logger.info(f"🤖 LLM 요청: {self.config.model} - {prompt[:50]}...")
        
        for attempt in range(self.config.retry_count + 1):
            try:
                with httpx.Client(timeout=self.config.timeout, headers=self.headers) as client:
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
                    
                    logger.info(f"✅ LLM 응답: {text[:50]}...")
                    return text
            except Exception as e:
                logger.warning(f"❌ Ollama 요청 실패 (시도 {attempt + 1}): {e}")
                logger.error(f"URL: {url}")
                logger.error(f"Payload: {payload}")
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
            elif "[" in clean_response or "{" in clean_response:
                # 배열 또는 객체 찾기
                if "[" in clean_response and clean_response.find("[") < clean_response.find("{"):
                    start = clean_response.find("[")
                    end = clean_response.rfind("]") + 1
                    json_str = clean_response[start:end]
                else:
                    # 첫 번째 JSON 객체만 추출 (여러 개가 있을 수 있음)
                    start = clean_response.find("{")
                    # 괄호 균형으로 첫 번째 JSON 끝 찾기
                    depth = 0
                    end = start
                    for i, c in enumerate(clean_response[start:], start):
                        if c == '{':
                            depth += 1
                        elif c == '}':
                            depth -= 1
                            if depth == 0:
                                end = i + 1
                                break
                    json_str = clean_response[start:end]

            data = json.loads(json_str)

            # 배열 응답 처리 (여러 액션이 반환된 경우 첫 번째만 사용)
            if isinstance(data, list):
                if not data:
                    logger.warning("빈 배열 응답 받음")
                    return None
                data = data[0]

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
            
            # 응답 검증: reason과 action의 일관성 체크
            reasoning = data.get("reasoning", "")
            if action_type == ActionType.BRV_ATTACK:
                # reason에 HP 공격 관련 키워드가 있으면 hp_attack으로 교정
                hp_keywords = ["HP 공격", "hp_attack", "HP공격", "HP 피해", "BREAK 상태"]
                if any(kw in reasoning for kw in hp_keywords):
                    logger.info(f"⚠️ 응답 교정: reason에 '{reasoning[:50]}...'이 있어 hp_attack으로 변경")
                    action_type = ActionType.HP_ATTACK
            
            return BotAction(
                action_type=action_type,
                target_name=data.get("target"),
                skill_id=data.get("skill_id"),
                item_id=data.get("item_id"),
                reasoning=reasoning,
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
        
        # 프로바이더별 클라이언트 초기화
        if self.config.provider == "openai":
            try:
                from src.ai.openai_client import OpenAIConfig, OpenAIClientSync
                openai_config = OpenAIConfig(
                    model=self.config.model if "gpt" in self.config.model else "gpt-4o-mini",
                    temperature=self.config.temperature,
                    max_tokens=self.config.max_tokens,
                    timeout=self.config.timeout,
                )
                self.client = OpenAIClientSync(openai_config)
                logger.info(f"[{bot_name}] OpenAI 프로바이더 사용: {openai_config.model}")
            except Exception as e:
                logger.warning(f"[{bot_name}] OpenAI 초기화 실패, Ollama 폴백: {e}")
                self.client = OllamaClientSync(self.config)
        else:
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
    
    def _analyze_combat_situation(self, combat_state: CombatState) -> PlayStyle:
        """
        현재 전투 상황을 분석하여 적절한 플레이 스타일 결정

        Returns:
            결정된 플레이 스타일
        """
        # 현재 캐릭터 찾기
        current_char = None
        for ally in combat_state.allies:
            if ally.name == combat_state.current_actor and ally.is_alive:
                current_char = ally
                break

        if not current_char:
            return self.config.play_style

        # 상황 분석
        self_hp_ratio = current_char.hp / current_char.max_hp if current_char.max_hp > 0 else 1.0
        self_mp_ratio = current_char.mp / current_char.max_mp if current_char.max_mp > 0 else 1.0
        self_brv_ratio = current_char.brv / current_char.max_brv if current_char.max_brv > 0 else 0.0

        # 아군 위험 상태 확인
        allies_in_danger = sum(1 for a in combat_state.allies
                               if a.is_alive and a.hp < a.max_hp * 0.3)
        allies_low_hp = sum(1 for a in combat_state.allies
                            if a.is_alive and a.hp < a.max_hp * 0.5)
        allies_dead = sum(1 for a in combat_state.allies if not a.is_alive)

        # 적 상황 분석
        alive_enemies = [e for e in combat_state.enemies if e.is_alive]
        total_enemy_hp = sum(e.hp for e in alive_enemies)
        enemy_count = len(alive_enemies)
        broken_enemies = sum(1 for e in alive_enemies if e.is_broken)
        low_brv_enemies = sum(1 for e in alive_enemies
                              if e.max_brv > 0 and e.brv / e.max_brv < 0.3)

        # 보스전 인식
        is_boss = combat_state.boss_name is not None
        if is_boss:
            # 보스전은 보수적 전략 우선
            if self_hp_ratio < 0.5 or allies_in_danger >= 1:
                return PlayStyle.DEFENSIVE
            if self_mp_ratio < 0.3:
                return PlayStyle.RESOURCE_SAVER
            return PlayStyle.BALANCED

        # 아군 사망자 있으면 긴급 방어 모드
        if allies_dead > 0 and allies_in_danger >= 1:
            return PlayStyle.DEFENSIVE

        # 플레이 스타일 동적 결정

        # 1. 자신이 위험하거나 아군이 여럿 위험 -> 방어적
        if self_hp_ratio < 0.3 or allies_in_danger >= 2:
            return PlayStyle.DEFENSIVE

        # 2. 아군 중 누군가 위험 -> 방어적
        if allies_in_danger > 0:
            return PlayStyle.DEFENSIVE

        # 3. 다수 적 BRV 낮음 -> BREAK 연타 기회 -> 공격적
        if low_brv_enemies >= 2 and self_hp_ratio > 0.5:
            return PlayStyle.AGGRESSIVE

        # 4. MP가 거의 없음 -> 절약형
        if self_mp_ratio < 0.2 and enemy_count > 1:
            return PlayStyle.RESOURCE_SAVER

        # 5. 장기전 감지 (턴 15 이상 + 적 HP 많음) -> 자원 절약
        if combat_state.turn_count >= 15 and total_enemy_hp > 1000:
            return PlayStyle.RESOURCE_SAVER

        # 6. 적이 1마리 남음 -> 스피드런 (빠른 처치)
        if enemy_count == 1 and alive_enemies[0].hp < alive_enemies[0].max_hp * 0.4:
            return PlayStyle.SPEEDRUN

        # 7. 여러 적이 있고 자신의 HP가 충분 -> 공격적
        if enemy_count >= 2 and self_hp_ratio > 0.6 and self_brv_ratio > 0.5:
            return PlayStyle.AGGRESSIVE

        # 8. 적이 BREAK 상태 + 자신의 BRV 높음 -> 공격적
        if broken_enemies > 0 and self_brv_ratio > 0.6:
            return PlayStyle.AGGRESSIVE

        # 9. 적의 총 HP가 낮고 아군이 안정적 -> 스피드런
        if total_enemy_hp < 500 and allies_low_hp == 0:
            return PlayStyle.SPEEDRUN

        # 기본값: 균형
        return PlayStyle.BALANCED

    def _get_system_prompt(self, combat_state: Optional[CombatState] = None) -> str:
        """
        현재 설정과 전투 상황에 맞는 시스템 프롬프트 생성

        Args:
            combat_state: 현재 전투 상태 (있으면 상황 분석해서 스타일 결정)
        """
        # 상황이 주어지면 동적으로 플레이 스타일 결정
        style = self.config.play_style
        if combat_state:
            style = self._analyze_combat_situation(combat_state)

        return get_system_prompt(
            style=style,
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
                context += f"\n## {name} 정보 (전적: {mem.times_won}/{mem.times_fought})\n"
                if mem.weaknesses:
                    context += f"- 약점: {', '.join(mem.weaknesses)}\n"
                if mem.attack_patterns:
                    context += f"- 패턴: {', '.join(mem.attack_patterns[:3])}\n"
                if mem.dangerous_moves:
                    context += f"- 위험 기술: {', '.join(mem.dangerous_moves)}\n"
                if mem.successful_strategies:
                    context += f"- 효과적 전략: {mem.successful_strategies[-1]}\n"
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

        # 기본 전략: 살아있는 적 중 가장 위협적인 대상 선택
        focus_target = None
        if combat_state.enemies:
            # 살아있는 적들 중에서 선택
            alive_enemies = [e for e in combat_state.enemies if e.is_alive]
            if alive_enemies:
                # 가장 높은 HP를 가진 적을 우선 타겟 (가장 위협적)
                focus_target = max(alive_enemies, key=lambda e: e.hp).name

        return PartyStrategy(
            focus_target=focus_target
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
            
            # 파티 전략 컨텍스트 추가 (보스전에서만)
            if is_boss and self.current_strategy:
                strategy_text = f"\n## 파티 전략\n"
                if self.current_strategy.focus_target:
                    strategy_text += f"- 기본 타겟: {self.current_strategy.focus_target} (상황에 따라 변경 가능)\n"
                if self.current_strategy.emergency_plan:
                    strategy_text += f"- 위기 대응: {self.current_strategy.emergency_plan}\n"
                if strategy_text != f"\n## 파티 전략\n":  # 실제 전략 정보가 있을 때만 추가
                    prompt = strategy_text + prompt
            
            # 히스토리 추가 (최근 2개만 - 속도 위해)
            if self.combat_history:
                history_text = "최근:" + "/".join(self.combat_history[-2:])
                prompt = history_text + "\n" + prompt
            
            # LLM 호출 (현재 상황에 맞는 플레이 스타일 동적 결정)
            system_prompt = self._get_system_prompt(combat_state)
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

                # 플레이 데이터 로깅 (RL 학습용)
                try:
                    from src.ai.play_data_logger import PlayDataLogger
                    if hasattr(self, '_play_logger') and self._play_logger:
                        self._play_logger.log_step(
                            state=asdict(combat_state),
                            action={"action_type": action.action_type.value, "target": action.target_name, "skill_id": action.skill_id},
                            reward=0.0,  # 실시간 보상은 나중에 계산
                            done=False
                        )
                except Exception:
                    pass

                return action
            else:
                fallback_act = self._fallback_action(combat_state)
                if self.on_commentary:
                    self.on_commentary(f"💡 {fallback_act.reasoning}")
                return fallback_act
                
        except Exception as e:
            logger.error(f"[{self.bot_name}] LLM 호출 오류: {e}")
            fallback_act = self._fallback_action(combat_state)
            if self.on_commentary:
                self.on_commentary(f"💡 {fallback_act.reasoning}")
            return fallback_act
    
    def decide_action(
        self,
        character: Any = None,
        allies: List[Any] = None,
        enemies: List[Any] = None,
        combat_state: Optional[CombatState] = None
    ) -> BotAction:
        """
        호환성 메서드: EnemyAI의 인터페이스를 맞추기 위한 래퍼

        Args:
            character: 현재 캐릭터 (선택사항)
            allies: 아군 목록 (선택사항)
            enemies: 적군 목록 (선택사항)
            combat_state: 전투 상태 객체 (우선)

        Returns:
            BotAction: 결정된 행동
        """
        # combat_state가 없으면 인자들로부터 구성
        if not combat_state and allies is not None and enemies is not None:
            # EnemyAI 인터페이스에서 호출된 경우: combat_state 생성
            # 주의: 이는 대략적인 상태 구성이므로 완전하지 않을 수 있음
            from src.combat.combat_manager import CombatState
            combat_state = CombatState(
                allies=allies,
                enemies=enemies,
                current_actor=character
            )

        if combat_state:
            return self.decide_combat_action(combat_state)
        else:
            logger.warning("[LLMPlayerBot] decide_action 호출 시 필요한 정보 부족")
            return self._fallback_action(None)

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
    
    def _get_job_role(self) -> Dict[str, bool]:
        """직업 역할 판별"""
        job_key = self.job_id.lower().replace(" ", "_") if self.job_id else "warrior"
        return {
            'is_healer': job_key in ['priest', 'cleric', 'druid', 'paladin'],
            'is_buffer': job_key in ['bard', 'knight', 'time_mage', 'engineer', 'shaman'],
            'is_tank': job_key in ['paladin', 'dimensionist', 'knight', 'warrior'],
            'is_debuffer': job_key in ['hacker', 'necromancer', 'shaman'],
            'job_key': job_key,
        }

    def _find_skill_by_type(self, skills: List[SkillInfo], skill_types: List[str], mp: int) -> Optional[SkillInfo]:
        """특정 타입의 사용 가능한 스킬 찾기"""
        for s in skills:
            if s.mp_cost > mp:
                continue
            if s.cooldown_remaining > 0:
                continue
            s_type = (s.skill_type or '').lower()
            s_id = (s.id or '').lower()
            s_desc = (s.description or '').lower()
            s_name = (s.name or '').lower()
            for t in skill_types:
                if t in s_type or t in s_id or t in s_desc or t in s_name:
                    return s
        return None

    def _fallback_action(self, combat_state: CombatState) -> BotAction:
        """폴백 행동 (LLM 실패 시) - 매우 강화된 직업 역할 기반 지능형 AI"""
        self.fallback_actions += 1

        # 현재 행동자 찾기
        current_ally = next((a for a in combat_state.allies if a.name == combat_state.current_actor), None)

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

        alive_allies = [a for a in combat_state.allies if a.is_alive]

        # 기본 상태값
        hp_ratio = current_ally.hp / current_ally.max_hp if current_ally.max_hp > 0 else 1.0
        mp = current_ally.mp
        brv = current_ally.brv
        max_brv = current_ally.max_brv if current_ally.max_brv > 0 else 1
        brv_ratio = brv / max_brv
        gimmick_value = current_ally.gimmick_value or 0

        # 직업 역할 판별
        role = self._get_job_role()
        # MP가 충분하고 쿨다운이 없는 스킬 필터링
        skills = [s for s in combat_state.available_skills if s.mp_cost <= mp and s.cooldown_remaining == 0]

        # 전략적 타겟 선택 (우선순위: BREAK > 적 BRV 높음 > 적 HP 낮음)
        def calc_priority(e):
            priority = 0
            if e.is_broken:
                priority += 500  # 브레이크된 적 최우선 (HP 딜 찬스)
                
            e_hp_pct = e.hp / e.max_hp if e.max_hp > 0 else 1.0
            if e_hp_pct < 0.2:
                priority += 400  # 딸피 적 마무리
            elif e_hp_pct < 0.5:
                priority += 100
                
            e_brv_pct = e.brv / e.max_brv if e.max_brv > 0 else 1.0
            if e_brv_pct > 0.8:
                priority += 300  # 적 BRV가 높아 브레이크 위험
            elif e_brv_pct < 0.3:
                priority += 150  # 브레이크 내기 쉬운 적
                
            # 체력이 낮은 적에게 보너스 점수 (일점사 유도)
            priority -= e.hp * 0.1 
            return priority

        target = max(alive_enemies, key=calc_priority)

        # ===== 0. 위급 상황: HP 위험 시 회복 (모든 역할 공통) =====
        if hp_ratio < 0.35:
            heal_skill = self._find_skill_by_type(skills, ['heal', '회복', '치유', 'cure', '빛', 'holy'], mp)
            if heal_skill:
                target_ally = current_ally
                if heal_skill.target_type in ["all_allies", "party"] or "전체" in (heal_skill.description or ""):
                    target_ally = None
                return BotAction(
                    action_type=ActionType.SKILL,
                    skill_id=heal_skill.id,
                    target_name=target_ally.name if target_ally else None,
                    reasoning=f"폴백(긴급): 생존을 위해 {heal_skill.name} 자힐"
                )
            for item in combat_state.available_items:
                if "회복" in item.effect or "HP" in item.effect.upper() or "포션" in item.name:
                    return BotAction(
                        action_type=ActionType.ITEM,
                        item_id=item.id,
                        target_name=current_ally.name,
                        reasoning=f"폴백(긴급): {item.name} 사용"
                    )

        # ===== 1. 힐러: 아군 보호 =====
        if role['is_healer']:
            critical_allies = [a for a in alive_allies if (a.hp / a.max_hp) < 0.6]
            if critical_allies:
                worst_ally = min(critical_allies, key=lambda a: a.hp / a.max_hp)
                heal_skill = self._find_skill_by_type(skills, ['heal', '회복', '치유', 'cure', 'holy', '기도', '축복'], mp)
                if heal_skill:
                    tgt_name = None if (heal_skill.target_type in ["all_allies", "party"] or "전체" in (heal_skill.description or "")) else worst_ally.name
                    return BotAction(
                        action_type=ActionType.SKILL,
                        skill_id=heal_skill.id,
                        target_name=tgt_name,
                        reasoning=f"폴백(힐러): 아군 보호 → {heal_skill.name}"
                    )
            buff_skill = self._find_skill_by_type(skills, ['buff', '강화', '버프', '보호', '축복', 'aura', 'barrier'], mp)
            if buff_skill:
                return BotAction(
                    action_type=ActionType.SKILL,
                    skill_id=buff_skill.id,
                    target_name=current_ally.name,
                    reasoning=f"폴백(힐러): 아군 강화 → {buff_skill.name}"
                )

        # ===== 2. 탱커: 어그로 및 방어 =====
        if role['is_tank']:
            weak_allies = [a for a in alive_allies if a.name != current_ally.name and (a.hp / a.max_hp) < 0.5]
            if weak_allies:
                taunt_skill = self._find_skill_by_type(skills, ['taunt', '도발', 'provoke', 'shield', '보호', 'iron_will', 'oath', '방패'], mp)
                if taunt_skill:
                    tgt_name = target.name if taunt_skill.target_type in ["enemy", "single_enemy"] else current_ally.name
                    return BotAction(
                        action_type=ActionType.SKILL,
                        skill_id=taunt_skill.id,
                        target_name=tgt_name,
                        reasoning=f"폴백(탱커): 아군 보호 → {taunt_skill.name}"
                    )
            if hp_ratio < 0.5 and brv_ratio < 0.5:
                return BotAction(action_type=ActionType.DEFEND, reasoning="폴백(탱커): 방어로 생존")

        # ===== 3. 버퍼 / 디버퍼: 보조 스킬 우선 =====
        if role['is_buffer']:
            buff_skill = self._find_skill_by_type(skills, ['buff', '강화', '버프', 'inspire', 'march', 'song', 'haste', '가속'], mp)
            if buff_skill:
                return BotAction(
                    action_type=ActionType.SKILL,
                    skill_id=buff_skill.id,
                    target_name=current_ally.name,
                    reasoning=f"폴백(버퍼): 파티 강화 → {buff_skill.name}"
                )
        if role['is_debuffer']:
            debuff_skill = self._find_skill_by_type(skills, ['debuff', '약화', '저주', 'curse', 'slow', 'blind', 'poison', 'virus', 'hack', '디버프', '침묵'], mp)
            if debuff_skill:
                return BotAction(
                    action_type=ActionType.SKILL,
                    skill_id=debuff_skill.id,
                    target_name=target.name,
                    reasoning=f"폴백(디버퍼): 적 약화 → {debuff_skill.name}"
                )

        # ===== 4. 딜러 (약점 공략 & 기믹 방출) =====
        weakness_skill = None
        weakness_str = getattr(target, 'element_weakness', '')
        if weakness_str:
            weaknesses = [w.strip().lower() for w in weakness_str.split(',') if w.strip()]
            for s in skills:
                desc_lower = (s.description or "").lower()
                name_lower = (s.name or "").lower()
                if any(w in desc_lower or w in name_lower for w in weaknesses):
                    weakness_skill = s
                    break
                
        if weakness_skill:
            return BotAction(
                action_type=ActionType.SKILL,
                skill_id=weakness_skill.id,
                target_name=target.name,
                reasoning=f"폴백(딜러): 약점 공략 → {weakness_skill.name}"
            )

        if gimmick_value >= 70:
            release_skill = self._find_skill_by_type(skills, ['burst', 'release', 'hadou', 'storm', 'mega', 'surge', 'bisect', 'execution', 'explosion', '방출', '폭발', '필살'], mp)
            if release_skill:
                return BotAction(
                    action_type=ActionType.SKILL,
                    skill_id=release_skill.id,
                    target_name=target.name,
                    reasoning=f"폴백(딜러): 기믹 {gimmick_value}% 폭발 → {release_skill.name}"
                )

        # MP 여유 시 주력기(가장 비싼 스킬) 사용
        if mp > current_ally.max_mp * 0.3:
            attack_skills = [s for s in skills if any(kw in (s.skill_type or '').lower() or kw in (s.description or '').lower() for kw in ['brv', 'attack', 'hp', 'strike', 'slash', 'hit', '공격', '피해', '데미지'])]
            if attack_skills:
                best_attack = max(attack_skills, key=lambda s: s.mp_cost)
                return BotAction(
                    action_type=ActionType.SKILL,
                    skill_id=best_attack.id,
                    target_name=target.name,
                    reasoning=f"폴백(딜러): 주력 스킬 → {best_attack.name}"
                )

        # ===== 5. 기본 공격 (BRV vs HP) =====
        if brv >= max_brv * 0.7 or target.is_broken:
            return BotAction(
                action_type=ActionType.HP_ATTACK,
                target_name=target.name,
                reasoning=f"폴백: BRV {brv_ratio:.0%} / Break 상태 → HP 공격!"
            )
            
        if target.brv > target.max_brv * 0.6:
            return BotAction(
                action_type=ActionType.BRV_ATTACK,
                target_name=target.name,
                reasoning=f"폴백: 적 BRV 높음 → BRV 공격으로 깎기"
            )

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
        
        # 아이템 변환 (소비 가능한 아이템: consumable, food)
        items = []
        if inventory is not None:
            from src.equipment.item_system import ItemType
            # 소비 가능한 아이템 타입 가져오기
            usable_types = [ItemType.CONSUMABLE, ItemType.FOOD]
            for item_type in usable_types:
                item_indices = inventory.get_items_by_type(item_type)
                for idx in item_indices:
                    item = inventory.get_item(idx)
                    if item:
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
    def from_town_manager(
        town_manager: Any,
        party: List[Any],
        inventory: Any,
        shop: Any = None
    ) -> TownState:
        """
        TownManager에서 TownState 생성
        
        Args:
            town_manager: TownManager 인스턴스
            party: 파티원 리스트
            inventory: Inventory 인스턴스
            shop: Shop 인스턴스 (선택)
        """
        # 파티 HP/MP 평균
        total_hp_pct = 0
        total_mp_pct = 0
        count = 0
        for char in party:
            if getattr(char, 'is_alive', True):
                max_hp = getattr(char, 'max_hp', 1)
                max_mp = getattr(char, 'max_mp', 1)
                total_hp_pct += getattr(char, 'current_hp', max_hp) / max_hp * 100
                total_mp_pct += getattr(char, 'current_mp', max_mp) / max_mp * 100
                count += 1
        
        party_hp = total_hp_pct / count if count > 0 else 100
        party_mp = total_mp_pct / count if count > 0 else 100
        
        # 인벤토리 정보
        gold = getattr(inventory, 'gold', 0)
        items = []
        sellable = []
        weight = 0
        max_weight = 20
        
        if hasattr(inventory, 'slots'):
            for slot in inventory.slots:
                if slot and hasattr(slot, 'item') and slot.item:
                    item = slot.item
                    item_data = {
                        "id": getattr(item, 'item_id', getattr(item, 'id', '')),
                        "name": getattr(item, 'name', ''),
                        "quantity": getattr(slot, 'quantity', 1)
                    }
                    items.append(item_data)
                    
                    # 판매 가능 여부 (재료, 잡화 등)
                    item_type = getattr(item, 'item_type', '')
                    if item_type in ['material', 'misc', 'junk']:
                        sellable.append(item_data["id"])
            
            weight = getattr(inventory, 'current_weight', 0)
            max_weight = getattr(inventory, 'max_weight', 20)
        
        # 시설 레벨
        facilities = {}
        if hasattr(town_manager, 'facilities'):
            for f_type, facility in town_manager.facilities.items():
                facilities[f_type.value if hasattr(f_type, 'value') else str(f_type)] = facility.level
        
        # 상점 아이템
        shop_items = []
        if shop and hasattr(shop, 'items'):
            for item in shop.items:
                shop_items.append({
                    "id": getattr(item, 'item_id', getattr(item, 'id', '')),
                    "name": getattr(item, 'name', ''),
                    "price": getattr(item, 'price', 0)
                })
        
        # 손상된 장비
        damaged = []
        for char in party:
            if hasattr(char, 'equipment'):
                for slot, equip in char.equipment.items():
                    if equip and hasattr(equip, 'durability'):
                        if equip.durability < equip.max_durability * 0.3:
                            damaged.append(getattr(equip, 'name', slot))
        
        # 요리 가능한 레시피 (간단히)
        recipes = []
        ingredients = []
        # 실제 구현은 CookingSystem과 연동 필요
        
        return TownState(
            party_hp_percent=party_hp,
            party_mp_percent=party_mp,
            gold=gold,
            inventory_items=items,
            sellable_items=sellable,
            inventory_weight=weight,
            max_weight=max_weight,
            facilities=facilities,
            shop_items=shop_items,
            available_recipes=recipes,
            cooking_ingredients=ingredients,
            damaged_equipment=damaged,
            ready_for_dungeon=(party_hp >= 80 and party_mp >= 50)
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
    model: str = "gemini-3-flash-preview",
    style: PlayStyle = PlayStyle.BALANCED,
    enable_thinking: bool = False,  # thinking 모드 끔 (빈 응답 방지)
    enable_commentary: bool = True,
    async_mode: bool = True,
    provider: str = None,  # "openai" or "ollama" (None=자동감지)
) -> LLMPlayerBot:
    """
    간편하게 LLM 봇 생성

    Args:
        name: 봇 이름
        job_id: 직업 ID (warrior, knight, archmage, cleric 등)
        model: LLM 모델명 (Ollama Cloud: gemini-3-flash-preview, OpenAI: gpt-4o-mini)
        style: 플레이 스타일
        enable_thinking: Qwen3 thinking 모드 활성화
        enable_commentary: 실시간 해설 활성화
        async_mode: 비동기 모드 (게임 프레임 드롭 방지)
        provider: "openai" 또는 "ollama" (None이면 API 키로 자동 결정)

    Returns:
        LLMPlayerBot 인스턴스
    """
    import uuid
    # 프로바이더 자동 감지: OPENAI_API_KEY → openai, OLLAMA_API_KEY → ollama cloud, 그 외 → ollama 로컬
    if provider is None:
        if os.environ.get("OPENAI_API_KEY"):
            provider = "openai"
        else:
            provider = "ollama"

    # Ollama Cloud 자동 감지: OLLAMA_API_KEY가 있으면 cloud 모드
    use_cloud = bool(os.environ.get("OLLAMA_API_KEY")) if provider == "ollama" else False

    config = LLMConfig(
        model=model,
        play_style=style,
        enable_thinking=enable_thinking,
        enable_commentary=enable_commentary,
        async_mode=async_mode,
        provider=provider,
        use_cloud=use_cloud,
    )
    return LLMPlayerBot(
        bot_id=str(uuid.uuid4()),
        bot_name=name,
        job_id=job_id,
        config=config
    )


def create_party_bots(
    party_config: List[Dict[str, str]],
    model: str = "gemini-3-flash-preview",
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
    inventory: Any = None,
    screen_text: str = ""
) -> BotAction:
    """
    CombatManager에서 봇 행동 결정 (게임 통합용)
    
    Args:
        bot: LLMPlayerBot 인스턴스
        combat_manager: CombatManager 인스턴스
        current_character: 현재 행동할 캐릭터
        inventory: 인벤토리 (선택)
        screen_text: 콘솔 화면 텍스트 (실제 플레이어가 보는 화면)
        
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
    
    # 화면 텍스트 추가 (실제 플레이어가 보는 화면)
    combat_state.screen_text = screen_text
    
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
                # variants 파생 스킬: greedy 변형 주입 (t_082c6a99)
                try:
                    from src.character.llm_bot_helpers import apply_variant_to_action_skill
                    seal_state = {
                        e: int(getattr(actor, f"seal_{e}", 0) or 0) for e in ("fire", "ice", "thunder", "wind")
                    }
                    apply_variant_to_action_skill(skill, seal_state)
                except Exception:
                    pass
                result = combat_manager.execute_action(actor, "skill", target=target, skill=skill)
            else:
                result = {"action": "skill", "success": False, "error": f"스킬 없음: {action.skill_id}"}
                
        elif action.action_type == ActionType.ITEM:
            if inventory and action.item_id:
                # 아이템 찾기
                item = None
                item_index = None
                from src.equipment.item_system import ItemType

                # 소비 가능한 아이템 타입 확인
                usable_types = [ItemType.CONSUMABLE, ItemType.FOOD]

                # slots를 순회하며 아이템 찾기
                for idx, slot in enumerate(inventory.slots):
                    if slot and slot.item:
                        # 아이템 타입 확인
                        item_type = getattr(slot.item, 'item_type', None)
                        if item_type in usable_types:
                            inv_item = slot.item
                            item_id = getattr(inv_item, 'id', getattr(inv_item, 'item_id', ''))
                            if item_id == action.item_id:
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
        # 프로바이더별 클라이언트 초기화
        if self.config.provider == "openai":
            try:
                from src.ai.llm_provider import create_provider
                self.client = create_provider("openai")
            except Exception as e:
                logger.warning(f"OpenAI 프로바이더 초기화 실패, Ollama 폴백: {e}")
                self.client = OllamaClientSync(self.config)
        else:
            self.client = OllamaClientSync(self.config)
        self.combat_bots: Dict[str, LLMPlayerBot] = {}
        self.logger = get_logger("auto_play_ai")
        
    def recommend_party(self, available_jobs: List[str], num_members: int = 4, randomize: bool = True) -> List[PartySetupChoice]:
        """
        파티 구성 추천
        
        Args:
            available_jobs: 사용 가능한 직업 목록
            num_members: 파티원 수
            randomize: True면 버그 헌팅용 랜덤 선택
        """
        import random
        
        # 버그 헌팅 모드: 다양한 직업 테스트
        if randomize:
            # 사용 가능한 직업에서 랜덤하게 선택
            shuffled = available_jobs.copy()
            random.shuffle(shuffled)
            selected = shuffled[:num_members]
            
            results = []
            for job_id in selected:
                info = JOB_DATABASE.get(job_id, {})
                name = info.get('name', job_id)
                gimmick = info.get('gimmick', '')
                results.append(PartySetupChoice(
                    job_id=job_id,
                    character_name=gimmick if gimmick else name,
                    reasoning=f"버그헌팅: {job_id}"
                ))
            
            self.logger.info(f"랜덤 파티 구성: {[r.job_id for r in results]}")
            return results
        
        # LLM 추천 모드
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
        
        # 폴백: 랜덤 선택
        shuffled = available_jobs.copy()
        random.shuffle(shuffled)
        return [
            PartySetupChoice(job_id, JOB_DATABASE.get(job_id, {}).get('name', job_id), reasoning="폴백")
            for job_id in shuffled[:num_members]
        ]
    
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
    
    def recommend_passives(
        self, 
        available_passives: List[Dict], 
        party_jobs: List[str],
        max_cost: int = 10,
        max_count: int = 3
    ) -> List[str]:
        """
        패시브 추천 (코스트 맞춰서)
        
        Args:
            available_passives: 사용 가능한 패시브 목록 [{"id", "name", "cost", "description"}]
            party_jobs: 파티 직업 목록
            max_cost: 최대 코스트 (기본 10)
            max_count: 최대 개수 (기본 3)
            
        Returns:
            추천 패시브 ID 목록
        """
        # 해금된 패시브만 필터
        unlocked = [p for p in available_passives if p.get('unlocked', True)]
        
        if not unlocked:
            return []
        
        # 규칙 기반 선택 (빠름)
        selected = []
        total_cost = 0
        
        # 파티 구성 분석
        has_tank = any(j in ['knight', 'paladin', 'gladiator'] for j in party_jobs)
        has_healer = any(j in ['cleric', 'priest', 'druid'] for j in party_jobs)
        has_mage = any(j in ['archmage', 'elementalist', 'time_mage'] for j in party_jobs)
        
        # 우선순위 키워드
        priority_keywords = []
        if has_tank:
            priority_keywords.extend(['방어', 'HP', '피해감소', 'defense', 'guard'])
        if has_healer:
            priority_keywords.extend(['회복', '힐', 'MP', 'heal', 'regen'])
        if has_mage:
            priority_keywords.extend(['마법', '주문', '원소', 'magic', 'spell'])
        
        # 일반 우선순위
        priority_keywords.extend(['공격력', '크리티컬', '속도', 'attack', 'critical', 'speed'])
        
        # 코스트 효율 순으로 정렬 (낮은 코스트 우선)
        sorted_passives = sorted(unlocked, key=lambda p: p.get('cost', 999))
        
        # 우선순위 키워드 매칭하는 패시브 먼저 선택
        for passive in sorted_passives:
            if len(selected) >= max_count:
                break
            
            cost = passive.get('cost', 1)
            if total_cost + cost > max_cost:
                continue
            
            # 키워드 매칭 확인
            desc = passive.get('description', '').lower() + passive.get('name', '').lower()
            if any(kw.lower() in desc for kw in priority_keywords):
                selected.append(passive.get('id'))
                total_cost += cost
        
        # 아직 슬롯이 남았으면 나머지 패시브 중 선택
        for passive in sorted_passives:
            if len(selected) >= max_count:
                break
            if passive.get('id') in selected:
                continue
            
            cost = passive.get('cost', 1)
            if total_cost + cost <= max_cost:
                selected.append(passive.get('id'))
                total_cost += cost
        
        self.logger.info(f"패시브 추천: {selected} (총 코스트: {total_cost}/{max_cost})")
        return selected
    
    def recommend_passives_llm(
        self, 
        available_passives: List[Dict], 
        party_jobs: List[str],
        max_cost: int = 10,
        max_count: int = 3
    ) -> List[str]:
        """패시브 추천 (LLM 사용 - 더 정확하지만 느림)"""
        unlocked = [p for p in available_passives if p.get('unlocked', True)]
        
        passives_text = "\n".join([
            f"- {p.get('id')} (코스트:{p.get('cost',1)}): {p.get('name','')} - {p.get('description','')[:40]}"
            for p in unlocked[:15]
        ])
        
        prompt = f"""파티 직업: {', '.join(party_jobs)}
최대 코스트: {max_cost}, 최대 개수: {max_count}

패시브 목록:
{passives_text}

코스트 합이 {max_cost} 이하가 되도록 최적의 패시브를 선택하세요.
JSON: [{{"id":"패시브ID","cost":코스트}}]"""

        try:
            response = self.client.generate(prompt, "패시브 전문가")
            import json
            import re
            json_match = re.search(r'\[.*\]', response, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
                # 코스트 검증
                total = sum(item.get('cost', 0) for item in data)
                if total <= max_cost and len(data) <= max_count:
                    return [item.get('id') for item in data if item.get('id')]
        except Exception as e:
            self.logger.warning(f"LLM 패시브 추천 실패: {e}")
        
        # 폴백: 규칙 기반
        return self.recommend_passives(available_passives, party_jobs, max_cost, max_count)
    
    def recommend_equipment(self, character: Any, inventory_items: List[Any]) -> Dict[str, Any]:
        """
        캐릭터에게 최적 장비 추천
        
        Args:
            character: 캐릭터 객체
            inventory_items: 인벤토리 아이템 목록
            
        Returns:
            {"slot": 장비슬롯, "item": 추천 아이템, "reason": 이유}
        """
        recommendations = {}
        
        job = getattr(character, 'character_class', '')
        
        # 직업별 우선 스탯
        stat_priority = {
            'warrior': ['physical_attack', 'hp', 'defense'],
            'knight': ['defense', 'hp', 'physical_attack'],
            'archmage': ['magic_attack', 'mp', 'speed'],
            'cleric': ['magic_attack', 'mp', 'hp'],
            'rogue': ['physical_attack', 'speed', 'critical'],
            'archer': ['physical_attack', 'speed', 'accuracy'],
        }
        priority = stat_priority.get(job, ['physical_attack', 'defense', 'hp'])
        
        for item in inventory_items:
            item_type = getattr(item, 'item_type', None)
            if not item_type:
                continue
            
            slot = item_type.value if hasattr(item_type, 'value') else str(item_type)
            if slot not in ['weapon', 'armor', 'accessory']:
                continue
            
            current_equip = character.equipment.get(slot) if hasattr(character, 'equipment') else None
            
            # 스탯 점수 계산
            def calc_score(equip):
                if not equip:
                    return -999
                score = 0
                for i, stat_name in enumerate(priority):
                    stat_val = getattr(equip, stat_name, 0)
                    if hasattr(equip, 'stats') and isinstance(equip.stats, dict):
                        stat_val = equip.stats.get(stat_name, 0)
                    score += stat_val * (3 - i)  # 우선순위에 따라 가중치
                
                # 내구도 보정
                durability = getattr(equip, 'durability', 100)
                max_dur = getattr(equip, 'max_durability', 100)
                if max_dur > 0:
                    score *= (durability / max_dur)
                
                return score
            
            new_score = calc_score(item)
            current_score = calc_score(current_equip)
            
            if new_score > current_score:
                if slot not in recommendations or new_score > recommendations[slot]['score']:
                    recommendations[slot] = {
                        'item': item,
                        'score': new_score,
                        'reason': f"{job} 직업에 적합 (점수: {new_score:.1f})"
                    }
        
        return recommendations
    
    def decide_town_action(self, state: TownState) -> TownAction:
        """
        마을 행동 결정 (규칙 기반 - 빠름)
        
        우선순위:
        1. HP/MP 회복 (파티 HP < 100%)
        2. 장비 수리 (손상된 장비가 있으면)
        3. 포션/아이템 구매 (포션 부족 시)
        4. 요리 제작 (재료가 있으면)
        5. 불필요한 아이템 판매 (무게 초과 시)
        6. 던전 출발 (준비 완료 시)
        """
        # 1. HP/MP 회복
        if state.party_hp_percent < 100 or state.party_mp_percent < 100:
            return TownAction("rest", reasoning="파티 회복 필요")
        
        # 2. 장비 수리
        if state.damaged_equipment:
            return TownAction("repair", target=state.damaged_equipment[0], reasoning="장비 수리")
        
        # 3. 포션 구매 (포션이 부족하면)
        has_potion = any("potion" in item.get("id", "").lower() for item in state.inventory_items)
        if not has_potion and state.gold >= 50:
            # 상점에서 포션 찾기
            for item in state.shop_items:
                if "potion" in item.get("id", "").lower():
                    return TownAction("buy", target=item.get("id"), quantity=3, reasoning="포션 보충")
        
        # 4. 요리 제작
        if state.available_recipes and state.cooking_ingredients:
            return TownAction("cook", target=state.available_recipes[0], reasoning="버프 요리 제작")
        
        # 5. 무게 초과 시 판매
        if state.inventory_weight > state.max_weight * 0.8 and state.sellable_items:
            return TownAction("sell", target=state.sellable_items[0], reasoning="무게 정리")
        
        # 6. 던전 출발
        return TownAction("depart", reasoning="던전 출발 준비 완료")
    
    def decide_town_actions_batch(self, state: TownState) -> List[TownAction]:
        """마을에서 할 모든 행동 목록 반환 (한 번에 처리)"""
        actions = []
        
        # 1. 회복
        if state.party_hp_percent < 100:
            actions.append(TownAction("rest", reasoning="회복"))
        
        # 2. 장비 수리
        for equip in state.damaged_equipment:
            actions.append(TownAction("repair", target=equip, reasoning="수리"))
        
        # 3. 포션 구매
        has_potion = sum(1 for item in state.inventory_items if "potion" in item.get("id", "").lower())
        if has_potion < 3 and state.gold >= 100:
            actions.append(TownAction("buy", target="hp_potion", quantity=3-has_potion, reasoning="포션 보충"))
        
        # 4. 요리
        if state.available_recipes:
            actions.append(TownAction("cook", target=state.available_recipes[0], reasoning="버프 요리"))
        
        # 5. 판매
        if state.inventory_weight > state.max_weight * 0.7:
            for item in state.sellable_items[:3]:
                actions.append(TownAction("sell", target=item, reasoning="무게 정리"))
        
        # 6. 출발
        actions.append(TownAction("depart", reasoning="던전 출발"))
        
        return actions

    def decide_exploration_action(self, state: ExplorationState) -> ExplorationAction:
        """탐험 행동 결정 (LLM 기반)"""
        
        # 프롬프트 생성
        prompt = self._build_exploration_prompt(state)
        
        try:
            response = self.client.generate(prompt, EXPLORATION_SYSTEM_PROMPT)
            return self._parse_exploration_response(response, state)
        except Exception as e:
            self.logger.warning(f"LLM 탐험 결정 실패: {e}, 규칙 기반 폴백")
            return self._fallback_exploration_action(state)
    
    def _build_exploration_prompt(self, state: ExplorationState) -> str:
        """탐험 프롬프트 생성"""
        px, py = state.current_position
        
        # 환경 정보
        hazard_info = ""
        if state.hazard_tiles:
            hazard_list = [f"- ({h['pos'][0]}, {h['pos'][1]}): {h.get('type', 'unknown')} (데미지: {h.get('damage', '?')})" 
                          for h in state.hazard_tiles[:5]]
            hazard_info = f"\n위험 타일:\n" + "\n".join(hazard_list)
        
        # 오브젝트 정보
        object_info = ""
        if state.objects:
            obj_list = [f"- ({o['pos'][0]}, {o['pos'][1]}): {o.get('type', 'unknown')}" 
                       for o in state.objects[:5]]
            object_info = f"\n상호작용 오브젝트:\n" + "\n".join(obj_list)
        
        # 회복 아이템 정보
        healing_info = ""
        if state.healing_items:
            item_list = [f"- {h['name']}: 회복량 {h.get('heal', '?')}, 보유 {h.get('count', 0)}개" 
                        for h in state.healing_items]
            healing_info = f"\n회복 아이템:\n" + "\n".join(item_list)
        
        # 보물/적 정보
        treasure_info = f"보물: {state.treasure_positions[:3]}" if state.treasure_positions else "보물: 없음"
        enemy_info = f"적: {state.nearby_enemies}" if state.nearby_enemies else "적: 없음"
        stairs_info = f"계단: {state.stairs_down_position}" if state.stairs_down_position else "계단: 미발견"
        
        prompt = f"""현재 상황:
- 위치: ({px}, {py})
- 층: {state.current_floor + 1}F ({state.floor_type})
- 탐험: {state.discovered_rooms}/{state.total_rooms} 방
- HP: {state.party_hp_percent:.0f}%
- MP: {state.party_mp_percent:.0f}%
- 골드: {state.gold}
{hazard_info}
{object_info}
{healing_info}
{treasure_info}
{enemy_info}
{stairs_info}

JSON 형식으로 행동 결정:
{{"action": "move|interact|use_item|fight|flee|pickup|open_chest", "target": "(x,y) 또는 아이템명", "avoid_hazards": true/false, "reason": "이유"}}"""
        
        return prompt
    
    def _parse_exploration_response(self, response: str, state: ExplorationState) -> ExplorationAction:
        """LLM 탐험 응답 파싱"""
        import json
        import re
        
        try:
            # JSON 추출
            json_match = re.search(r'\{[^{}]*\}', response, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
                action_type = data.get("action", "move")
                target = data.get("target", "")
                avoid_hazards = data.get("avoid_hazards", True)
                reason = data.get("reason", "LLM 결정")
                
                # 타겟 파싱
                target_position = None
                item_to_use = None
                direction = None
                
                if isinstance(target, str) and "," in target:
                    # (x, y) 형식
                    coords = re.findall(r'-?\d+', target)
                    if len(coords) >= 2:
                        target_position = (int(coords[0]), int(coords[1]))
                elif isinstance(target, str) and action_type == "use_item":
                    item_to_use = target
                elif isinstance(target, list) and len(target) == 2:
                    target_position = tuple(target)
                
                return ExplorationAction(
                    action_type=action_type,
                    direction=direction,
                    target=target if isinstance(target, str) else None,
                    target_position=target_position,
                    item_to_use=item_to_use,
                    avoid_hazards=avoid_hazards,
                    reasoning=reason
                )
        except Exception as e:
            self.logger.warning(f"탐험 응답 파싱 실패: {e}")
        
        return self._fallback_exploration_action(state)
    
    def _fallback_exploration_action(self, state: ExplorationState) -> ExplorationAction:
        """폴백 탐험 행동 (규칙 기반)"""
        import random
        
        # 1. HP 낮으면 회복
        if state.party_hp_percent < 30:
            if state.healing_items:
                return ExplorationAction("use_item", item_to_use=state.healing_items[0].get('name', 'potion'), reasoning="HP 위험 - 회복")
            if state.has_healing_point:
                return ExplorationAction("rest", reasoning="HP 낮음, 회복")
        
        # 2. 오브젝트 파밍 (보물상자 등)
        if state.objects:
            obj = state.objects[0]
            return ExplorationAction("interact", target_position=obj['pos'], target=obj.get('type'), reasoning="오브젝트 파밍")
        
        # 3. 보물 수집
        if state.treasure_positions:
            return ExplorationAction("move", target_position=state.treasure_positions[0], reasoning="보물 수집")
        
        # 4. 적 처리
        if state.nearby_enemies:
            if state.party_hp_percent > 50:
                return ExplorationAction("fight", reasoning="적 발견, 전투")
            return ExplorationAction("flee", reasoning="HP 낮음, 회피")
        
        # 5. 계단 이동
        if state.stairs_down_position and state.discovered_rooms >= state.total_rooms * 0.7:
            return ExplorationAction("move", target_position=state.stairs_down_position, reasoning="다음 층")
        
        # 6. 미탐험 방향 탐색
        if state.unexplored_directions:
            unexplored = random.choice(state.unexplored_directions)
            px, py = state.current_position
            target_x = px + unexplored[0] * 10
            target_y = py + unexplored[1] * 10
            return ExplorationAction("move", target_position=(target_x, target_y), reasoning="미탐험 지역 탐색")
        
        # 7. 랜덤 탐색
        px, py = state.current_position
        random_target = (px + random.randint(-5, 5), py + random.randint(-5, 5))
        return ExplorationAction("move", target_position=random_target, reasoning="랜덤 탐색")
    
    def decide_town_action(self, state: TownState) -> TownAction:
        """마을 행동 결정 (LLM 기반)"""
        
        prompt = self._build_town_prompt(state)
        
        try:
            response = self.client.generate(prompt, TOWN_SYSTEM_PROMPT)
            return self._parse_town_response(response, state)
        except Exception as e:
            self.logger.warning(f"LLM 마을 결정 실패: {e}, 규칙 기반 폴백")
            return self._fallback_town_action(state)
    
    def _build_town_prompt(self, state: TownState) -> str:
        """마을 프롬프트 생성"""
        
        # 상점 아이템
        shop_info = ""
        if state.shop_items:
            items = [f"- {i.get('name', '?')}: {i.get('price', 0)}골드" for i in state.shop_items[:5]]
            shop_info = "\n상점 아이템:\n" + "\n".join(items)
        
        # 인벤토리
        inv_info = ""
        if state.inventory_items:
            items = [f"- {i.get('name', '?')} x{i.get('count', 1)}" for i in state.inventory_items[:5]]
            inv_info = "\n보유 아이템:\n" + "\n".join(items)
        
        prompt = f"""마을 상태:
- HP: {state.party_hp_percent:.0f}%
- MP: {state.party_mp_percent:.0f}%
- 골드: {state.gold}
- 인벤토리: {state.inventory_weight}/{state.max_weight}
{shop_info}
{inv_info}

JSON 형식으로 행동 결정:
{{"action": "buy|sell|repair|cook|craft|rest|upgrade|storage|depart", "target": "아이템명 또는 시설명", "quantity": 1, "reason": "이유"}}"""
        
        return prompt
    
    def _parse_town_response(self, response: str, state: TownState) -> TownAction:
        """LLM 마을 응답 파싱"""
        import json
        import re
        
        try:
            json_match = re.search(r'\{[^{}]*\}', response, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
                return TownAction(
                    action_type=data.get("action", "rest"),
                    target=data.get("target"),
                    quantity=data.get("quantity", 1),
                    reasoning=data.get("reason", "LLM 결정")
                )
        except Exception as e:
            self.logger.warning(f"마을 응답 파싱 실패: {e}")
        
        return self._fallback_town_action(state)
    
    def _fallback_town_action(self, state: TownState) -> TownAction:
        """폴백 마을 행동 (규칙 기반)"""
        
        # 1. HP 낮으면 휴식
        if state.party_hp_percent < 80:
            return TownAction("rest", reasoning="HP 회복")
        
        # 2. 회복 아이템 구매
        if state.gold >= 50:
            for item in state.shop_items:
                if "포션" in item.get('name', '') or "회복" in item.get('name', ''):
                    return TownAction("buy", target=item.get('name'), quantity=3, reasoning="회복 아이템 구매")
        
        # 3. 장비 수리
        if state.damaged_equipment:
            return TownAction("repair", target=state.damaged_equipment[0], reasoning="장비 수리")
        
        # 4. 던전 출발
        return TownAction("depart", reasoning="던전 출발")
    
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


def create_auto_play_ai(
    model: str = None,
    style: PlayStyle = PlayStyle.BALANCED,
    provider: str = None,
    **kwargs
) -> AutoPlayAI:
    """AutoPlayAI 인스턴스 생성 (프로바이더 선택)"""
    config = LLMConfig(play_style=style)

    if provider == "openai":
        config.provider = "openai"
    elif model:
        config.model = model
        config.provider = "ollama"

    return AutoPlayAI(config)
