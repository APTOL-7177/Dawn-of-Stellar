"""
튜토리얼 봇 조언자 시스템
Dawn of Stellar

게임의 모든 시스템을 완벽히 이해하고 상황에 맞는 조언을 제공하는 AI 봇
- 34개 직업 기믹 완벽 숙지
- ATB + BRV 전투 시스템 마스터
- 파티 시너지, 장비, 요리, 패시브 최적화
- 보스별 공략법
- 위기 상황 대처
"""

import time
import random
import math
from typing import Dict, Any, Optional, List, Set, Tuple, Callable
from dataclasses import dataclass, field
from enum import Enum, auto

from src.core.logger import get_logger, Loggers

logger = get_logger(Loggers.SYSTEM)


# =============================================================================
# 봇 성격 및 대사 스타일
# =============================================================================

class BotPersonality(Enum):
    """봇 성격"""
    SELENA = "selena"      # 친절하고 정확한 AI
    KARNOS = "karnos"      # 무뚝뚝한 전쟁 베테랑
    MIRA = "mira"          # 활발하고 호기심 많은 현자


@dataclass
class BotMessage:
    """봇 메시지"""
    text: str
    personality: BotPersonality = BotPersonality.SELENA
    priority: int = 0  # 높을수록 중요
    duration: float = 3.0  # 표시 시간
    category: str = ""  # 중복 방지용 카테고리


# =============================================================================
# 상황 감지 시스템
# =============================================================================

class SituationType(Enum):
    """상황 유형"""
    # 전투 기본
    FIRST_COMBAT = "first_combat"
    FIRST_BRV_ATTACK = "first_brv_attack"
    FIRST_HP_ATTACK = "first_hp_attack"
    FIRST_BREAK = "first_break"
    FIRST_SKILL_USE = "first_skill_use"
    
    # 위험 상황
    LOW_HP = "low_hp"
    CRITICAL_HP = "critical_hp"
    BRV_OVERFLOW_WARNING = "brv_overflow"
    PARTY_MEMBER_DOWN = "party_down"
    
    # 전략 조언
    ENEMY_WEAK_TO_ELEMENT = "enemy_weakness"
    ENEMY_BREAK_CHANCE = "break_chance"
    BREAK_STATE = "break_state"
    BOSS_ENCOUNTER = "boss_encounter"
    
    # 탐험
    FIRST_FLOOR = "first_floor"
    HEALING_POINT = "healing_point"
    TREASURE_FOUND = "treasure_found"
    EXIT_FOUND = "exit_found"
    
    # 메타
    LEVEL_UP = "level_up"
    NEW_SKILL_LEARNED = "new_skill"
    FLOOR_CLEARED = "floor_cleared"
    
    # 직업 기믹
    JOB_GIMMICK_HINT = "job_gimmick"


# =============================================================================
# 조언 데이터베이스
# =============================================================================

ADVICE_DATABASE: Dict[SituationType, List[Dict[str, Any]]] = {
    # === 전투 기본 ===
    SituationType.FIRST_COMBAT: [
        {"text": "첫 전투네요! 방향키로 메뉴 선택, Z로 확인이에요.", "personality": BotPersonality.SELENA},
        {"text": "ATB 게이지가 차면 행동할 수 있어요. 잘 보세요!", "personality": BotPersonality.SELENA},
    ],
    SituationType.FIRST_BRV_ATTACK: [
        {"text": "BRV 공격 선택! 적의 BRV를 깎고 내 BRV를 올려요.", "personality": BotPersonality.SELENA},
        {"text": "BRV를 쌓아야 HP 공격으로 피해를 줄 수 있어요.", "personality": BotPersonality.SELENA},
    ],
    SituationType.FIRST_HP_ATTACK: [
        {"text": "HP 공격! 쌓인 BRV만큼 적에게 피해를 줍니다.", "personality": BotPersonality.SELENA},
        {"text": "HP 공격 후 BRV는 초기화돼요. 다시 쌓아야 해요!", "personality": BotPersonality.SELENA},
    ],
    SituationType.FIRST_BREAK: [
        {"text": "BREAK 성공! 적 BRV가 0이 되면 발동해요.", "personality": BotPersonality.KARNOS},
        {"text": "BREAK 상태에서 HP 공격하면 보너스 데미지!", "personality": BotPersonality.KARNOS},
    ],
    SituationType.FIRST_SKILL_USE: [
        {"text": "스킬 사용! MP를 소모하지만 강력해요.", "personality": BotPersonality.MIRA},
        {"text": "각 직업마다 고유한 스킬이 있어요~", "personality": BotPersonality.MIRA},
    ],
    
    # === 위험 상황 ===
    SituationType.LOW_HP: [
        {"text": "HP가 낮아요! 힐러가 있으면 회복을, 아니면 조심하세요.", "personality": BotPersonality.SELENA, "priority": 5},
        {"text": "위험해요! 방어적으로 플레이하거나 회복을 고려하세요.", "personality": BotPersonality.SELENA, "priority": 5},
    ],
    SituationType.CRITICAL_HP: [
        {"text": "위험! HP가 너무 낮아요! 즉시 회복이 필요해요!", "personality": BotPersonality.SELENA, "priority": 10},
        {"text": "죽기 직전이야! 포션이나 힐링 스킬을 써!", "personality": BotPersonality.KARNOS, "priority": 10},
    ],
    SituationType.BRV_OVERFLOW_WARNING: [
        {"text": "BRV가 최대치에 가까워요! HP 공격으로 소비하세요.", "personality": BotPersonality.SELENA, "priority": 3},
        {"text": "BRV 넘치면 손해야. HP 공격해라.", "personality": BotPersonality.KARNOS, "priority": 3},
    ],
    SituationType.PARTY_MEMBER_DOWN: [
        {"text": "파티원이 쓰러졌어요! 부활 아이템이나 스킬을 사용하세요.", "personality": BotPersonality.SELENA, "priority": 7},
    ],
    
    # === 전략 조언 ===
    SituationType.ENEMY_WEAK_TO_ELEMENT: [
        {"text": "{element} 속성에 약해요! {element} 스킬을 쓰면 효과적!", "personality": BotPersonality.MIRA},
    ],
    SituationType.ENEMY_BREAK_CHANCE: [
        {"text": "적 BRV가 낮아요! 조금만 더 치면 BREAK!", "personality": BotPersonality.KARNOS},
    ],
    SituationType.BREAK_STATE: [
        {"text": "BREAK 상태! 지금 HP 공격하면 보너스 데미지!", "personality": BotPersonality.KARNOS, "priority": 5},
        {"text": "BREAK! 이 기회를 놓치지 마세요!", "personality": BotPersonality.SELENA, "priority": 5},
    ],
    SituationType.BOSS_ENCOUNTER: [
        {"text": "보스다! 패턴을 파악하고 신중하게 공략해라.", "personality": BotPersonality.KARNOS, "priority": 8},
        {"text": "보스전이에요! BRV 관리와 회복 타이밍이 중요해요.", "personality": BotPersonality.SELENA, "priority": 8},
    ],
    
    # === 탐험 ===
    SituationType.FIRST_FLOOR: [
        {"text": "던전에 입장했어요! 방향키로 이동, 적과 만나면 전투!", "personality": BotPersonality.SELENA},
        {"text": "출구(>)를 찾아서 다음 층으로 내려가세요.", "personality": BotPersonality.SELENA},
    ],
    SituationType.HEALING_POINT: [
        {"text": "회복 포인트예요! 여기서 HP/MP를 회복할 수 있어요.", "personality": BotPersonality.SELENA},
    ],
    SituationType.TREASURE_FOUND: [
        {"text": "보물이에요! 열어보세요~", "personality": BotPersonality.MIRA},
    ],
    SituationType.EXIT_FOUND: [
        {"text": "출구를 찾았어요! 준비됐으면 다음 층으로!", "personality": BotPersonality.SELENA},
    ],
    
    # === 메타 ===
    SituationType.LEVEL_UP: [
        {"text": "레벨 업! 스탯이 올랐어요!", "personality": BotPersonality.MIRA},
    ],
    SituationType.NEW_SKILL_LEARNED: [
        {"text": "새 스킬을 배웠어요! 전투에서 사용해보세요.", "personality": BotPersonality.MIRA},
    ],
    SituationType.FLOOR_CLEARED: [
        {"text": "{floor}층 클리어! 잘하고 있어요!", "personality": BotPersonality.SELENA},
        {"text": "좋아, {floor}층 돌파. 계속 가자.", "personality": BotPersonality.KARNOS},
    ],
    
    # === 직업 기믹 ===
    SituationType.JOB_GIMMICK_HINT: [
        {"text": "{job_hint}", "personality": BotPersonality.MIRA},
    ],
}

# =============================================================================
# 34개 직업 완전 데이터베이스 (실제 게임 직업만!)
# =============================================================================

JOB_DATABASE: Dict[str, Dict[str, Any]] = {
    # === 전사 계열 ===
    "warrior": {
        "name": "전사",
        "role": "물리 딜러/탱커",
        "gimmick": "스탠스 시스템",
        "gimmick_desc": "6가지 스탠스(공격/방어/속도/회피/집중/균형)를 전환하며 상황 대응",
        "tips": [
            "보스전에선 방어 스탠스로 시작해서 패턴 파악 후 공격 스탠스로!",
            "속도 스탠스로 ATB 우위를 점하면 행동 순서 조절 가능!",
            "회피 스탠스는 강공격 예고 시 유용해요!",
            "집중 스탠스는 크리티컬로 BRV를 빠르게 쌓을 때!",
        ],
        "synergy": ["cleric", "bard", "knight"],
        "counter": ["high_magic_enemies"],
    },
    "knight": {
        "name": "기사",
        "role": "탱커/서포터",
        "gimmick": "의무 스택",
        "gimmick_desc": "도발/방어 시 의무 스택 축적, 스택 소모로 파티 보호",
        "tips": [
            "의무 스택 3개 이상이면 즉시 파티 피해 대신 받기 가능!",
            "도발로 적 타겟을 고정하고 다른 딜러를 보호하세요!",
            "보스 강공격 전에 의무 스택을 미리 쌓아두세요!",
            "힐러와 함께하면 거의 무적의 탱킹이 가능해요!",
        ],
        "synergy": ["cleric", "archmage", "berserker"],
        "counter": ["multi_target_enemies"],
    },
    "archmage": {
        "name": "아크메이지",
        "role": "마법 딜러",
        "gimmick": "원소 조합",
        "gimmick_desc": "화염/빙결/번개 원소를 조합해 대마법 시전",
        "tips": [
            "같은 원소 3개 = 해당 속성 대마법!",
            "3종류 조합 = 프리즘 버스트(전체 무속성 대데미지)!",
            "적 속성 약점에 맞는 원소를 우선 사용하세요!",
            "MP 관리가 중요해요! 잡몹에겐 기본 마법으로 아껴두세요!",
        ],
        "synergy": ["bard", "scholar", "enchanter"],
        "counter": ["magic_resistant"],
    },
    "cleric": {
        "name": "성직자",
        "role": "힐러/버퍼",
        "gimmick": "신앙 포인트",
        "gimmick_desc": "힐/버프 시 신앙 축적, 대기도로 강력한 효과",
        "tips": [
            "신앙 5 이상이면 대기도로 파티 전체 풀힐 가능!",
            "예방 힐보다 HP 50% 이하일 때 힐이 더 효율적!",
            "버프는 보스전 시작 시 미리 걸어두세요!",
            "부활 스킬은 신앙 3 필요, 항상 여유분 확보!",
        ],
        "synergy": ["knight", "paladin", "warrior"],
        "counter": ["heal_block_enemies"],
    },
    "archer": {
        "name": "궁수",
        "role": "물리 딜러",
        "gimmick": "집중 게이지",
        "gimmick_desc": "집중 축적으로 크리티컬률/데미지 증가",
        "tips": [
            "집중 MAX에서 필살은 거의 확정 크리티컬!",
            "이동하면 집중이 초기화되니 위치 선점이 중요!",
            "약점 조준으로 방어 무시, 탱커 적에게 효과적!",
            "다중 화살은 BRV 빠르게 쌓기 좋아요!",
        ],
        "synergy": ["bard", "dancer", "ranger"],
        "counter": ["high_evasion_enemies"],
    },
    "berserker": {
        "name": "버서커",
        "role": "물리 딜러",
        "gimmick": "광폭화",
        "gimmick_desc": "HP가 낮을수록 공격력/속도 증가",
        "tips": [
            "HP 30% 이하면 공격력 2배! 위험하지만 강력!",
            "힐러와 함께 HP를 적절히 유지하며 딜링!",
            "광폭화 상태에서 BREAK 보너스는 엄청난 데미지!",
            "포션 대신 힐러 힐로 HP 조절이 더 정밀해요!",
        ],
        "synergy": ["cleric", "knight", "bard"],
        "counter": ["instant_death_enemies"],
    },
    
    # === 고급 직업 ===
    "paladin": {
        "name": "팔라딘",
        "role": "탱커/힐러",
        "gimmick": "신성 보호막",
        "gimmick_desc": "자신과 아군에게 피해 흡수 보호막 부여",
        "tips": [
            "보호막은 HP 힐과 별개라 중첩 가능!",
            "보스 강공격 전에 파티 전체 보호막!",
            "자힐이 있어서 힐러 없이도 버틸 수 있어요!",
            "신성 스매시는 언데드에게 2배 데미지!",
        ],
        "synergy": ["cleric", "archmage", "bard"],
        "counter": ["dark_enemies"],
    },
    "dark_knight": {
        "name": "다크나이트",
        "role": "물리 딜러",
        "gimmick": "HP 소모 공격",
        "gimmick_desc": "HP를 소모해 강력한 공격, 처치 시 HP 흡수",
        "tips": [
            "적 처치 시 HP 30% 회복되니 과감하게!",
            "암흑검은 HP 소모 대신 BRV 전환도 가능!",
            "힐러 없이 솔로 플레이도 가능한 자급자족!",
            "HP가 낮을 때 흡혈 공격으로 역전!",
        ],
        "synergy": ["berserker", "necromancer", "vampire"],
        "counter": ["heal_block_enemies"],
    },
    "samurai": {
        "name": "사무라이",
        "role": "물리 딜러",
        "gimmick": "기합 카운터",
        "gimmick_desc": "피격 시 기합 축적, 발도술로 대데미지",
        "tips": [
            "일부러 맞아서 기합을 쌓는 전략도 유효!",
            "기합 MAX 발도술은 보스도 한방 컷 가능!",
            "카운터가 있어서 탱킹하며 딜링 가능!",
            "명경지수로 다음 공격 100% 회피!",
        ],
        "synergy": ["knight", "berserker", "monk"],
        "counter": ["magic_enemies"],
    },
    "monk": {
        "name": "무투가",
        "role": "물리 딜러/서포터",
        "gimmick": "기 순환",
        "gimmick_desc": "기 축적으로 스킬 강화, 파티 버프",
        "tips": [
            "기 5에서 쓰는 스킬은 효과 2배!",
            "기공파는 원거리 공격 가능한 물리!",
            "차크라로 자힐 가능, 힐러 부담 감소!",
            "기 나눔으로 파티원 MP/HP 회복 지원!",
        ],
        "synergy": ["bard", "cleric", "dancer"],
        "counter": ["defense_pierce_enemies"],
    },
    
    # === 마법 직업 ===
    "time_mage": {
        "name": "시간술사",
        "role": "서포터/디버퍼",
        "gimmick": "시간 조작",
        "gimmick_desc": "ATB 조작, 헤이스트/슬로우로 전장 지배",
        "tips": [
            "헤이스트 파티 버프로 행동 순서 장악!",
            "슬로우는 보스 ATB를 크게 늦춰요!",
            "스톱은 낮은 확률이지만 성공 시 무적 타임!",
            "퀵은 아군 즉시 행동! 긴급 상황에!",
        ],
        "synergy": ["any"],  # 모든 파티에 좋음
        "counter": ["time_immune_enemies"],
    },
    
    # === 특수 직업 ===
    "bard": {
        "name": "음유시인",
        "role": "버퍼/서포터",
        "gimmick": "노래",
        "gimmick_desc": "지속 버프 노래, 중첩 가능",
        "tips": [
            "공격의 노래 + 마력의 노래 중첩 가능!",
            "진혼곡으로 적 수면, 잡몹 무력화!",
            "노래 유지 중에도 기본 공격 가능!",
            "레퀴엠은 즉사기, 운 좋으면 보스도!",
        ],
        "synergy": ["any"],
        "counter": ["silence_enemies"],
    },
    "alchemist": {
        "name": "연금술사",
        "role": "유틸",
        "gimmick": "조합",
        "gimmick_desc": "아이템 조합으로 강력한 효과",
        "tips": [
            "포션 + 포션 = 하이포션 즉석 제조!",
            "폭탄 계열은 원소 데미지!",
            "아이템 2배 사용 패시브와 시너지!",
            "비약으로 파티 전체 버프 가능!",
        ],
        "synergy": ["chemist", "any"],
        "counter": ["item_seal_enemies"],
    },
    
    # === 추가 직업들 ===
    "necromancer": {
        "name": "강령술사",
        "role": "마법 딜러/소환",
        "gimmick": "언데드 소환",
        "gimmick_desc": "죽은 적을 언데드로 부활",
        "tips": [
            "처치한 적을 아군으로! 보스 부하도 가능!",
            "언데드는 HP 대신 지속시간 관리!",
            "다크 계열 마법 특화!",
            "생명력 흡수로 자힐!",
        ],
        "synergy": ["dark_knight", "vampire", "summoner"],
        "counter": ["holy_enemies"],
    },
    "vampire": {
        "name": "흡혈귀",
        "role": "물리 딜러",
        "gimmick": "흡혈",
        "gimmick_desc": "공격 시 HP 흡수, 피에 따른 강화",
        "tips": [
            "흡혈로 힐러 없이도 지속 전투 가능!",
            "핏빛 광란 상태에서 공격력 2배!",
            "밤/어둠 지형에서 모든 능력 강화!",
            "박쥐 변신으로 회피 및 이동!",
        ],
        "synergy": ["necromancer", "dark_knight", "assassin"],
        "counter": ["holy_enemies", "garlic_items"],
    },
    "druid": {
        "name": "드루이드",
        "role": "힐러/변신",
        "gimmick": "자연 변신",
        "gimmick_desc": "동물 변신으로 역할 변경",
        "tips": [
            "곰 = 탱커, 늑대 = 딜러, 새 = 회피!",
            "자연 치유는 지속 회복!",
            "정령 소환으로 원소 공격!",
            "변신 해제 시 HP 회복!",
        ],
        "synergy": ["ranger", "shaman", "elementalist"],
        "counter": ["polymorph_enemies"],
    },
    "assassin": {
        "name": "암살자",
        "role": "물리 딜러",
        "gimmick": "암살 표식",
        "gimmick_desc": "표식 부여 후 처형으로 즉사/대데미지",
        "tips": [
            "표식 3중첩 후 처형 = 확정 크리티컬!",
            "은신 상태에서 기습 = 2배 데미지!",
            "독 특화, 지속 데미지 강력!",
            "HP 25% 이하 적에게 즉사 확률!",
        ],
        "synergy": ["ninja", "thief", "ranger"],
        "counter": ["mark_immune_enemies"],
    },
    "elementalist": {
        "name": "정령술사",
        "role": "마법 딜러",
        "gimmick": "정령 계약",
        "gimmick_desc": "4대 정령과 계약, 상황별 전환",
        "tips": [
            "화 정령 = 공격, 수 정령 = 회복!",
            "풍 정령 = 속도, 지 정령 = 방어!",
            "정령 합체로 대폭발 피니셔!",
            "정령 전환은 무료, 자주 바꿔가며!",
        ],
        "synergy": ["summoner", "geomancer", "druid"],
        "counter": ["element_absorb_enemies"],
    },
    "shaman": {
        "name": "주술사",
        "role": "디버퍼/힐러",
        "gimmick": "저주/축복",
        "gimmick_desc": "강력한 지속 디버프, 아군 버프",
        "tips": [
            "저주는 중첩 가능! 3중첩은 매우 강력!",
            "토템 설치로 지역 버프/디버프!",
            "정화로 아군 디버프 제거!",
            "영혼 연결로 파티 생존력 공유!",
        ],
        "synergy": ["necromancer", "druid", "witch"],
        "counter": ["curse_immune_enemies"],
    },
    "battle_mage": {
        "name": "배틀메이지",
        "role": "물리/마법 하이브리드",
        "gimmick": "마법 무장",
        "gimmick_desc": "마법을 물리 공격에 결합",
        "tips": [
            "마법검으로 물리+마법 동시 데미지!",
            "마나 실드로 MP를 방어에 사용!",
            "물/마 둘 다 약한 적에게 최강!",
            "마력 폭발로 축적 마나 일시 방출!",
        ],
        "synergy": ["warrior", "archmage", "enchanter"],
        "counter": ["adaptive_enemies"],
    },
    "pirate": {
        "name": "해적",
        "role": "물리 딜러/유틸",
        "gimmick": "약탈",
        "gimmick_desc": "적 아이템/골드 약탈, 보물 감지",
        "tips": [
            "약탈로 희귀 아이템 강탈!",
            "대포 공격은 전체 물리!",
            "럼주로 자버프 + 자해!",
            "보물 감지로 숨겨진 상자 발견!",
        ],
        "synergy": ["thief", "gunner", "berserker"],
        "counter": ["nothing_to_steal"],
    },
    "gladiator": {
        "name": "검투사",
        "role": "물리 딜러",
        "gimmick": "관중 열광",
        "gimmick_desc": "화려한 플레이로 관중 열광, 버프 획득",
        "tips": [
            "콤보 공격으로 열광도 상승!",
            "열광 MAX에서 피니셔는 3배!",
            "도발로 1:1 결투 유도!",
            "승리의 함성으로 파티 사기 증가!",
        ],
        "synergy": ["bard", "dancer", "warrior"],
        "counter": ["audience_immune"],
    },
    "dimensionist": {
        "name": "차원술사",
        "role": "유틸/마법",
        "gimmick": "차원문",
        "gimmick_desc": "차원 이동, 공간 왜곡",
        "tips": [
            "차원문으로 즉시 탈출!",
            "공간 압축으로 적 이동 봉쇄!",
            "차원 칼날은 방어 무시!",
            "평행 세계 소환으로 분신!",
        ],
        "synergy": ["time_mage", "psychic", "summoner"],
        "counter": ["dimension_lock_enemies"],
    },
    "hacker": {
        "name": "해커",
        "role": "디버퍼/유틸",
        "gimmick": "시스템 해킹",
        "gimmick_desc": "적 스탯 조작, 버프 해제",
        "tips": [
            "스탯 해킹으로 적 약화!",
            "버프 해제로 적 강화 무효화!",
            "시스템 버그로 적 행동 오류!",
            "데이터 백업으로 아군 부활!",
        ],
        "synergy": ["machinist", "scholar", "psychic"],
        "counter": ["unhackable_enemies"],
    },
    
    "breaker": {
        "name": "브레이커",
        "role": "BRV 파괴 특화",
        "gimmick": "파괴력 축적",
        "gimmick_desc": "BRV 공격 시 파괴력 축적, 파괴력 비례 피해 증가",
        "tips": [
            "BRV 공격할수록 파괴력이 쌓여요! 10스택 목표!",
            "파괴력 5 이상이면 피해 +100%!",
            "파괴력 10이면 피해 +200%에 방어 관통!",
            "BREAK 내기 최고의 직업이에요!",
        ],
    },
    "dragon_knight": {
        "name": "용기사",
        "role": "화염 특화 딜러",
        "gimmick": "용의 표식",
        "gimmick_desc": "화염 속성 특화, 화상으로 추가 피해",
        "tips": [
            "화염 속성 데미지 +35%, 화염 저항 +50%!",
            "공격 시 50% 확률로 화상 부여!",
            "화상 상태 적 공격 시 데미지 +30%!",
            "회피 성공 시 화염 반격!",
        ],
    },
    "engineer": {
        "name": "기계공학자",
        "role": "장비 강화",
        "gimmick": "열 관리 시스템",
        "gimmick_desc": "열 게이지 관리, 최적 구간에서 보너스",
        "tips": [
            "열 50-79 (최적): 모든 스탯 +15%!",
            "열 80-99 (위험): 크리티컬 +20%!",
            "열 95 도달 시 자동 냉각 (전투당 2회)!",
            "최적 구간에서 MP 소모 -30%!",
        ],
    },
    "magician": {
        "name": "마술사",
        "role": "트릭스터 유틸",
        "gimmick": "트럼프 카드",
        "gimmick_desc": "카드 드로우로 포커 조합 발동",
        "tips": [
            "기본 공격 시 카드 2장 드로우!",
            "포커 조합 완성 시 강력한 스킬 발동!",
            "운이 좋으면 대박, 안 좋으면 쪽박!",
            "덱에 남은 카드 종류 확인 가능!",
        ],
    },
    "philosopher": {
        "name": "철학자",
        "role": "논리 조작",
        "gimmick": "선택 시스템",
        "gimmick_desc": "힘/지혜/희생 중 선택, 선택에 따른 강화",
        "tips": [
            "힘 5회 선택: 물리 공격 +60%, 크리 +30%!",
            "지혜 5회 선택: 마법 +60%, MP 재생!",
            "희생 5회 선택: 아군 사망 시 자동 부활!",
            "균형 선택: 모든 효과 골고루!",
        ],
    },
    "priest": {
        "name": "신관",
        "role": "기적/치유 특화",
        "gimmick": "신앙 & 심판력",
        "gimmick_desc": "치유 시 신앙, 공격 시 심판력 축적",
        "tips": [
            "신앙 축적으로 힐 효과 +30%!",
            "심판력 50 이상 시 신성 피해 +50%!",
            "신앙=심판력이면 모든 스킬 +40%!",
            "구원과 심판, 상황에 맞게!",
        ],
    },
    "rogue": {
        "name": "도적",
        "role": "속도형 딜러",
        "gimmick": "훔치기 시스템",
        "gimmick_desc": "압도적 속도와 회피, 훔친 아이템 활용",
        "tips": [
            "훔치기 성공률 +30%, 효과 +50%!",
            "회피 성공 시 아이템 +1, 크리 확정!",
            "훔친 아이템 5개 시 희귀 획득 2배!",
            "속도 최상급! ATB 압도적!",
        ],
    },
    "sniper": {
        "name": "저격수",
        "role": "초고화력 원거리",
        "gimmick": "탄창 시스템",
        "gimmick_desc": "6발 탄창, 재장전 타이밍이 핵심",
        "tips": [
            "마지막 탄환: 크리 +50%, 데미지 +30%!",
            "재장전 시 턴 소모 안 함 (2회)!",
            "30% 확률로 탄환 소모 없음!",
            "헤드샷 크리 시 5% 즉사!",
        ],
    },
    "spellblade": {
        "name": "마검사",
        "role": "하이브리드 딜러",
        "gimmick": "마나 블레이드",
        "gimmick_desc": "마법과 검술 융합, 마나 축적 강화",
        "tips": [
            "마나 블레이드 최대 120!",
            "원소 부여 피해 +40%!",
            "마나 50 이상: 물리+마법 동시!",
            "마나 100: 모든 스킬 2배!",
        ],
    },
    "sword_saint": {
        "name": "검성",
        "role": "폭발 딜러",
        "gimmick": "검기 시스템",
        "gimmick_desc": "검기로 폭발적 피해, 추가 공격 확률",
        "tips": [
            "물리 공격 시 검기 30% 추가!",
            "25% 확률 즉시 추가 공격!",
            "단일 타겟 집중: +40%!",
            "검 장착: 크리 +25%, 크뎀 +50%!",
        ],
    },
    "default": {
        "name": "???",
        "role": "???",
        "gimmick": "???",
        "gimmick_desc": "특별한 기믹이 있어요!",
        "tips": ["스킬을 확인해보세요!"],
        "synergy": [],
        "counter": [],
    },
}

# 간단 접근용 힌트 (기존 호환)
JOB_GIMMICK_HINTS: Dict[str, List[str]] = {
    job_id: data["tips"] for job_id, data in JOB_DATABASE.items()
}


# =============================================================================
# 요리 시스템 데이터베이스
# =============================================================================


COOKING_DATABASE: Dict[str, Dict[str, Any]] = {
    # === 초급 요리 ===
    "herb_soup": {
        "name": "약초 수프",
        "effect": "HP 50, MP 20 회복",
        "ingredients": ["herb x2"],
        "tips": "초반 탐험에 유용한 기본 회복!",
    },
    "mushroom_stew": {
        "name": "버섯 스튜",
        "effect": "HP 40, MP 40 회복 + 마법 버프",
        "ingredients": ["mushroom x3"],
        "tips": "마법 직업에게 좋은 초급 요리!",
    },
    "grilled_fish": {
        "name": "생선 구이",
        "effect": "HP 60, MP 10 회복",
        "ingredients": ["fish x1"],
        "tips": "물가에서 낚은 생선으로!",
    },
    "roasted_meat": {
        "name": "구운 고기",
        "effect": "HP 50 회복",
        "ingredients": ["meat x1"],
        "tips": "간단하고 효과적인 회복!",
    },
    "fruit_salad": {
        "name": "과일 샐러드",
        "effect": "HP 30, MP 30 회복",
        "ingredients": ["fruit x3"],
        "tips": "균형 잡힌 회복에 좋아요!",
    },
    
    # === 중급 요리 ===
    "honey_bread": {
        "name": "꿀빵",
        "effect": "HP 100, BRV 100 회복",
        "ingredients": ["dough x1", "honey x1"],
        "tips": "BRV 회복이 필요할 때!",
    },
    "fish_and_chips": {
        "name": "피쉬 앤 칩스",
        "effect": "HP 220 + 속도 버프",
        "ingredients": ["fish x1", "potato x2", "dough x1"],
        "tips": "속도가 필요한 전투 전에!",
    },
    "omurice": {
        "name": "오므라이스",
        "effect": "HP 250, MP 50 회복",
        "ingredients": ["rice x1", "egg x2", "tomato_sauce x1"],
        "tips": "균형 잡힌 중급 회복 요리!",
    },
    "cream_pasta": {
        "name": "크림 파스타",
        "effect": "HP 200, MP 100 + 방어 버프",
        "ingredients": ["dough x1", "cream x1", "milk x1"],
        "tips": "탱커에게 추천!",
    },
    
    # === 고급 요리 ===
    "pizza": {
        "name": "콤비네이션 피자",
        "effect": "HP 600, BRV 200 + 방어 버프",
        "ingredients": ["dough x1", "tomato_sauce x1", "cheese x1", "meat x1"],
        "tips": "파티 전체 회복에 좋아요!",
    },
    "carbonara": {
        "name": "까르보나라",
        "effect": "HP 550, MP 150 + 스태미나 버프",
        "ingredients": ["dough x1", "cream x1", "egg x1", "meat x1"],
        "tips": "긴 탐험 전에 추천!",
    },
    "steak_dinner": {
        "name": "스테이크 정식",
        "effect": "HP 800, MP 100 + 공격 버프",
        "ingredients": ["steak x1", "roasted_vegetables x1", "wine x1"],
        "tips": "보스전 전 딜러에게!",
    },
    
    # === 디저트 & 음료 ===
    "cheesecake": {
        "name": "치즈 케이크",
        "effect": "HP 200, MP 400 + 마법 버프",
        "ingredients": ["cheese x2", "cream x1", "egg x1", "sugar x1"],
        "tips": "MP가 부족한 마법 직업에게!",
    },
    "royal_milk_tea": {
        "name": "로얄 밀크티",
        "effect": "MP 300 + 침묵 해제 + 마방 버프",
        "ingredients": ["tea_leaf x1", "milk x2", "honey x1"],
        "tips": "침묵 상태이상에 특효!",
    },
    
    # === 특수 효과 요리 ===
    "antidote_salad": {
        "name": "해독 샐러드",
        "effect": "HP 100 + 독 해제",
        "ingredients": ["herb x2", "vegetable x1"],
        "tips": "독 상태이상에 특효!",
    },
    "fireproof_chili": {
        "name": "화염 저항 칠리",
        "effect": "HP 300 + 화염 저항 50%",
        "ingredients": ["meat x2", "spice x2", "tomato_sauce x1"],
        "tips": "용 같은 화염 보스 상대 시!",
    },
    "golden_apple_pie": {
        "name": "황금 사과 파이",
        "effect": "HP 1000, MP 500 + 크리티컬 20% + 행운 버프",
        "ingredients": ["golden_apple x1", "dough x1", "honey x1", "butter x1"],
        "tips": "최상급 희귀 요리! 보스전 필수!",
    },
}



STATUS_EFFECTS: Dict[str, Dict[str, Any]] = {
    # === DOT (지속 피해) ===
    "poison": {
        "name": "독",
        "type": "DOT",
        "effect": "매 턴 HP 감소",
        "cure": "해독 샐러드, 에스나",
        "tips": "힐러의 해독 스킬이나 해독 샐러드로 해제!",
    },
    "burn": {
        "name": "화상",
        "type": "DOT",
        "effect": "매 턴 HP 감소 + 방어력 감소",
        "cure": "물 계열 스킬, 시간 경과",
        "tips": "수호의 아이스크림으로 해제 가능!",
    },
    "bleed": {
        "name": "출혈",
        "type": "DOT",
        "effect": "매 턴 HP 감소, 이동 시 악화",
        "cure": "치유 스킬, 시간 경과",
        "tips": "이동을 최소화하고 빨리 치료!",
    },
    
    # === CC (행동 제약) ===
    "stun": {
        "name": "기절",
        "type": "CC",
        "effect": "1~2턴 행동 불가",
        "cure": "시간 경과",
        "tips": "BREAK 당하면 기절! 방어를 잘 하세요!",
    },
    "sleep": {
        "name": "수면",
        "type": "CC",
        "effect": "피해 받을 때까지 행동 불가",
        "cure": "피해 받기, 시간 경과",
        "tips": "아군 공격으로 깨울 수 있어요!",
    },
    "silence": {
        "name": "침묵",
        "type": "CC",
        "effect": "스킬 사용 불가 (기본 공격만)",
        "cure": "로얄 밀크티, 에스나",
        "tips": "마법 직업은 특히 주의!",
    },
    "paralyze": {
        "name": "마비",
        "type": "CC",
        "effect": "50% 확률로 행동 실패",
        "cure": "시간 경과, 정화 스킬",
        "tips": "운에 맡기지 말고 빨리 해제!",
    },
    "freeze": {
        "name": "빙결",
        "type": "CC",
        "effect": "행동 불가 + 물리 피해 증가",
        "cure": "화염 스킬, 따뜻한 생강차",
        "tips": "빙결 상태에서 물리 피해 2배!",
    },
    "blind": {
        "name": "실명",
        "type": "CC",
        "effect": "명중률 대폭 감소",
        "cure": "시간 경과, 정화",
        "tips": "물리 딜러는 특히 주의!",
    },
    "charm": {
        "name": "매혹",
        "type": "CC",
        "effect": "아군을 공격할 수 있음",
        "cure": "피해 받기, 시간 경과",
        "tips": "매혹 걸린 아군을 때려서 깨워요!",
    },
    
    # === 버프 ===
    "haste": {
        "name": "가속",
        "type": "BUFF",
        "effect": "ATB 충전 속도 증가",
        "tips": "시간술사의 핵심 버프!",
    },
    "regeneration": {
        "name": "재생",
        "type": "BUFF",
        "effect": "매 턴 HP 회복",
        "tips": "드루이드, 성직자가 제공!",
    },
    "invincible": {
        "name": "무적",
        "type": "BUFF",
        "effect": "모든 피해 무효",
        "tips": "지속시간 짧으니 보스 강공격 타이밍에!",
    },
    "berserk": {
        "name": "광폭화",
        "type": "BUFF",
        "effect": "공격력 증가, 방어력 감소, 행동 불가",
        "tips": "버서커 전용! 위험하지만 강력!",
    },
}



DUNGEON_OBJECTS: Dict[str, Dict[str, Any]] = {
    "healing_fountain": {
        "name": "치유의 샘",
        "symbol": "F",
        "effect": "HP/MP 50% 회복",
        "tips": "파티 전원 회복! 보스 전에 아껴두세요!",
    },
    "cursed_altar": {
        "name": "저주받은 제단",
        "symbol": "A",
        "effect": "버프 OR 저주 (랜덤)",
        "tips": "운 좋으면 강력한 버프, 나쁘면 저주!",
    },
    "gamblers_table": {
        "name": "도박사의 테이블",
        "symbol": "G",
        "effect": "골드 베팅, 승패에 따른 보상",
        "tips": "고위험 고보상! 여유 골드가 있을 때만!",
    },
    "locked_chest": {
        "name": "잠긴 상자",
        "symbol": "C",
        "effect": "열쇠 필요, 좋은 아이템",
        "tips": "열쇠를 모아두세요! 희귀 아이템 가능!",
    },
    "mystery_statue": {
        "name": "신비한 석상",
        "symbol": "S",
        "effect": "퀴즈 정답 시 보상",
        "tips": "퀴즈를 풀면 보상! 게임 지식이 필요해요!",
    },
    "merchant": {
        "name": "떠돌이 상인",
        "symbol": "M",
        "effect": "아이템 구매/판매",
        "tips": "희귀 아이템 판매! 골드 아끼지 마세요!",
    },
    "shrine_of_strength": {
        "name": "힘의 성소",
        "symbol": "Σ",
        "effect": "물리 공격력 영구 증가",
        "tips": "물리 딜러에게 양보하세요!",
    },
    "shrine_of_wisdom": {
        "name": "지혜의 성소",
        "symbol": "Ω",
        "effect": "마법 공격력 영구 증가",
        "tips": "마법 딜러에게 양보하세요!",
    },
    "ancient_portal": {
        "name": "고대 포탈",
        "symbol": "P",
        "effect": "다른 층으로 이동",
        "tips": "숨겨진 층이나 보스 스킵 가능!",
    },
    "wishing_well": {
        "name": "소원의 우물",
        "symbol": "W",
        "effect": "골드 투척, 랜덤 효과",
        "tips": "골드를 던지면 소원이 이루어질지도?",
    },
}



COOKING_TIPS: List[str] = [
    "요리는 전투 전에 미리 만들어두세요!",
    "버프 요리는 보스전 직전에!",
    "재료는 채집 포인트나 몬스터 드랍으로!",
    "중간 재료(반죽, 버터 등)를 먼저 만들면 고급 요리 가능!",
    "회복 요리는 전투 중에도 아이템처럼 사용!",
]

OBJECT_TIPS: List[str] = [
    "치유의 샘은 보스 전에 아껴두세요!",
    "잠긴 상자 열쇠는 항상 모아두세요!",
    "도박사의 테이블은 여유 골드가 있을 때만!",
    "성소는 해당 역할 파티원에게!",
    "상인에게서 희귀 아이템 구입 가능!",
]

STATUS_TIPS: List[str] = [
    "BREAK 당하면 기절! BRV 관리 중요!",
    "침묵은 마법 직업에게 치명적!",
    "빙결 상태에서 물리 피해 2배!",
    "가속 버프로 행동 순서 장악!",
    "해독 샐러드로 독 해제!",
]

GATHERING_DATABASE: Dict[str, Dict[str, Any]] = {}
GATHERING_TIPS: List[str] = []
EQUIPMENT_DATABASE: Dict[str, Dict[str, Any]] = {}
EQUIPMENT_TIPS: List[str] = []
META_PROGRESSION: Dict[str, Dict[str, Any]] = {
    "stellar_fragments": {
        "name": "별의 파편",
        "tips": [
            "별의 파편으로 새 직업을 해금하세요!",
            "패시브 스킬도 별의 파편으로 구매!",
            "게임오버해도 별의 파편은 유지돼요!",
        ],
    },
}


class TutorialBot:
    """
    튜토리얼 봇 조언자
    
    게임 상황을 감지하고 적절한 조언을 제공합니다.
    """
    
    def __init__(self):
        self.enabled = True
        self.current_message: Optional[BotMessage] = None
        self.message_queue: List[BotMessage] = []
        self.message_start_time: float = 0
        
        # 이미 본 조언 추적 (중복 방지)
        self.seen_situations: Set[str] = set()
        self.seen_categories: Dict[str, float] = {}  # 카테고리별 마지막 표시 시간
        
        # 게임 상태 추적
        self.combat_count = 0
        self.brv_attack_count = 0
        self.hp_attack_count = 0
        self.break_count = 0
        self.skill_use_count = 0
        self.current_floor = 0
        
        # 쿨다운 (같은 카테고리 조언 반복 방지)
        self.category_cooldown = 30.0  # 초
        
        logger.info("튜토리얼 봇 초기화")
    
    def enable(self):
        """봇 활성화"""
        self.enabled = True
    
    def disable(self):
        """봇 비활성화"""
        self.enabled = False
        self.current_message = None
        self.message_queue.clear()
    
    def update(self, dt: float = 0.016):
        """봇 상태 업데이트 (매 프레임 호출)"""
        if not self.enabled:
            return
        
        current_time = time.time()
        
        # 현재 메시지 만료 체크
        if self.current_message:
            elapsed = current_time - self.message_start_time
            if elapsed >= self.current_message.duration:
                self.current_message = None
        
        # 큐에서 다음 메시지 가져오기
        if not self.current_message and self.message_queue:
            # 우선순위 정렬
            self.message_queue.sort(key=lambda m: -m.priority)
            self.current_message = self.message_queue.pop(0)
            self.message_start_time = current_time
    
    def get_current_message(self) -> Optional[BotMessage]:
        """현재 표시할 메시지 반환"""
        return self.current_message if self.enabled else None
    
    def notify_situation(self, situation: SituationType, context: Dict[str, Any] = None):
        """
        상황 발생 알림
        
        Args:
            situation: 상황 유형
            context: 추가 컨텍스트 (예: 속성, 층 번호 등)
        """
        if not self.enabled:
            return
        
        context = context or {}
        situation_key = f"{situation.value}_{hash(frozenset(context.items()))}"
        current_time = time.time()
        
        # 일회성 조언 체크
        one_time_situations = {
            SituationType.FIRST_COMBAT,
            SituationType.FIRST_BRV_ATTACK,
            SituationType.FIRST_HP_ATTACK,
            SituationType.FIRST_BREAK,
            SituationType.FIRST_SKILL_USE,
            SituationType.FIRST_FLOOR,
        }
        
        if situation in one_time_situations:
            if situation.value in self.seen_situations:
                return
            self.seen_situations.add(situation.value)
        
        # 카테고리 쿨다운 체크
        category = situation.value
        if category in self.seen_categories:
            if current_time - self.seen_categories[category] < self.category_cooldown:
                return
        
        # 조언 선택
        advice_list = ADVICE_DATABASE.get(situation, [])
        if not advice_list:
            return
        
        advice = random.choice(advice_list)
        text = advice["text"]
        
        # 컨텍스트 치환
        for key, value in context.items():
            text = text.replace(f"{{{key}}}", str(value))
        
        # 메시지 생성
        message = BotMessage(
            text=text,
            personality=advice.get("personality", BotPersonality.SELENA),
            priority=advice.get("priority", 0),
            duration=advice.get("duration", 3.0),
            category=category
        )
        
        self.message_queue.append(message)
        self.seen_categories[category] = current_time
        
        logger.debug(f"봇 조언 추가: {text}")
    
    # === 편의 메서드 ===
    
    def on_combat_start(self, is_boss: bool = False):
        """전투 시작"""
        self.combat_count += 1
        if self.combat_count == 1:
            self.notify_situation(SituationType.FIRST_COMBAT)
        if is_boss:
            self.notify_situation(SituationType.BOSS_ENCOUNTER)
    
    def on_brv_attack(self):
        """BRV 공격"""
        self.brv_attack_count += 1
        if self.brv_attack_count == 1:
            self.notify_situation(SituationType.FIRST_BRV_ATTACK)
    
    def on_hp_attack(self):
        """HP 공격"""
        self.hp_attack_count += 1
        if self.hp_attack_count == 1:
            self.notify_situation(SituationType.FIRST_HP_ATTACK)
    
    def on_break(self):
        """BREAK 발생"""
        self.break_count += 1
        if self.break_count == 1:
            self.notify_situation(SituationType.FIRST_BREAK)
    
    def on_skill_use(self):
        """스킬 사용"""
        self.skill_use_count += 1
        if self.skill_use_count == 1:
            self.notify_situation(SituationType.FIRST_SKILL_USE)
    
    def on_low_hp(self, hp_percent: float):
        """HP 부족"""
        if hp_percent <= 0.15:
            self.notify_situation(SituationType.CRITICAL_HP)
        elif hp_percent <= 0.3:
            self.notify_situation(SituationType.LOW_HP)
    
    def on_brv_overflow_warning(self):
        """BRV 오버플로우 경고"""
        self.notify_situation(SituationType.BRV_OVERFLOW_WARNING)
    
    def on_break_state(self):
        """적 BREAK 상태"""
        self.notify_situation(SituationType.BREAK_STATE)
    
    def on_floor_enter(self, floor: int):
        """층 진입"""
        self.current_floor = floor
        if floor == 1:
            self.notify_situation(SituationType.FIRST_FLOOR)
    
    def on_floor_clear(self, floor: int):
        """층 클리어"""
        self.notify_situation(SituationType.FLOOR_CLEARED, {"floor": floor})
    
    def on_healing_point(self):
        """회복 포인트 발견"""
        self.notify_situation(SituationType.HEALING_POINT)
    
    def on_job_first_use(self, job_id: str):
        """직업 첫 사용 (기믹 힌트)"""
        hints = JOB_GIMMICK_HINTS.get(job_id, JOB_GIMMICK_HINTS.get("default", ["스킬을 확인해보세요!"]))
        hint = random.choice(hints)
        self.notify_situation(SituationType.JOB_GIMMICK_HINT, {"job_hint": hint})
    
    # =========================================================================
    # 고급 전투 분석 시스템
    # =========================================================================
    
    def analyze_combat_situation(
        self,
        party: List[Any],
        enemies: List[Any],
        current_character: Any = None
    ) -> Optional[str]:
        """
        현재 전투 상황을 분석하고 최적의 조언 생성
        
        Args:
            party: 아군 파티
            enemies: 적 목록
            current_character: 현재 행동 캐릭터
        
        Returns:
            조언 문자열 또는 None
        """
        if not self.enabled or not party or not enemies:
            return None
        
        advice_list = []
        
        # === 파티 상태 분석 ===
        low_hp_members = []
        dead_members = []
        brv_overflow_risk = []
        
        for member in party:
            hp_percent = getattr(member, 'current_hp', 0) / max(getattr(member, 'max_hp', 1), 1)
            
            if hp_percent <= 0:
                dead_members.append(member)
            elif hp_percent <= 0.25:
                low_hp_members.append((member, hp_percent))
            
            # BRV 오버플로우 체크
            current_brv = getattr(member, 'current_brv', 0)
            max_brv = getattr(member, 'max_brv', 1000)
            if current_brv >= max_brv * 0.9:
                brv_overflow_risk.append(member)
        
        # === 적 상태 분석 ===
        breakable_enemies = []
        low_hp_enemies = []
        
        for enemy in enemies:
            enemy_brv = getattr(enemy, 'current_brv', 100)
            enemy_hp = getattr(enemy, 'current_hp', 100)
            enemy_max_hp = getattr(enemy, 'max_hp', 100)
            
            # BREAK 가능 적
            if enemy_brv <= 50:
                breakable_enemies.append(enemy)
            
            # 처치 가능 적
            if enemy_hp <= enemy_max_hp * 0.2:
                low_hp_enemies.append(enemy)
        
        # === 우선순위 조언 생성 ===
        
        # 1. 죽은 파티원 부활
        if dead_members:
            name = getattr(dead_members[0], 'name', '파티원')
            advice_list.append(f"⚠ {name}이(가) 쓰러졌어요! 부활 스킬이나 아이템을!")
        
        # 2. 위독한 파티원
        elif low_hp_members:
            member, hp_pct = low_hp_members[0]
            name = getattr(member, 'name', '파티원')
            advice_list.append(f"⚠ {name} HP {int(hp_pct*100)}%! 회복이 필요해요!")
        
        # 3. BRV 오버플로우 경고
        elif brv_overflow_risk and current_character in brv_overflow_risk:
            advice_list.append("BRV가 거의 꽉 찼어요! HP 공격으로 소비하세요!")
        
        # 4. BREAK 가능
        elif breakable_enemies:
            name = getattr(breakable_enemies[0], 'name', '적')
            advice_list.append(f"🎯 {name} BRV가 낮아요! 조금만 더 치면 BREAK!")
        
        # 5. 마무리 가능
        elif low_hp_enemies:
            name = getattr(low_hp_enemies[0], 'name', '적')
            advice_list.append(f"🎯 {name} HP가 낮아요! HP 공격으로 마무리!")
        
        if advice_list:
            advice = random.choice(advice_list)
            self._add_custom_message(advice, priority=5)
            return advice
        
        return None
    
    def get_job_strategy_advice(self, job_id: str, situation: str = "general") -> str:
        """
        직업별 전략 조언
        
        Args:
            job_id: 직업 ID
            situation: 상황 (general, boss, low_hp, buff_phase 등)
        
        Returns:
            조언 문자열
        """
        job_data = JOB_DATABASE.get(job_id, JOB_DATABASE["default"])
        tips = job_data.get("tips", ["스킬을 확인해보세요!"])
        
        # 상황별 필터링
        if situation == "boss":
            boss_tips = [t for t in tips if "보스" in t or "강공격" in t]
            if boss_tips:
                return random.choice(boss_tips)
        
        return random.choice(tips)
    
    def analyze_party_synergy(self, party_jobs: List[str]) -> str:
        """
        파티 시너지 분석
        
        Args:
            party_jobs: 파티 직업 ID 목록
        
        Returns:
            시너지 분석 결과
        """
        if not party_jobs:
            return "파티 정보가 없어요."
        
        roles = {"탱커": 0, "힐러": 0, "딜러": 0, "서포터": 0}
        
        for job_id in party_jobs:
            job_data = JOB_DATABASE.get(job_id, {})
            role = job_data.get("role", "???")
            
            if "탱커" in role:
                roles["탱커"] += 1
            if "힐러" in role:
                roles["힐러"] += 1
            if "딜러" in role:
                roles["딜러"] += 1
            if "서포터" in role or "버퍼" in role:
                roles["서포터"] += 1
        
        # 밸런스 분석
        warnings = []
        
        if roles["탱커"] == 0:
            warnings.append("탱커가 없어요! 피해 분산이 어려울 수 있어요.")
        if roles["힐러"] == 0:
            warnings.append("힐러가 없어요! 포션에 의존해야 해요.")
        if roles["딜러"] < 2:
            warnings.append("딜러가 부족해요! 전투가 길어질 수 있어요.")
        
        if not warnings:
            return "파티 밸런스가 좋아요! 다양한 역할이 갖춰졌어요."
        
        return warnings[0]
    
    def get_boss_strategy(self, boss_id: str) -> List[str]:
        """
        보스별 공략 조언
        
        Args:
            boss_id: 보스 ID
        
        Returns:
            공략 조언 목록
        """
        # 보스별 공략 데이터베이스
        boss_strategies = {
            "time_devourer": [
                "시간 포식자는 3턴마다 전체 공격을 해요! 미리 방어 준비!",
                "시간 정지 스킬을 쓰면 2턴간 무적이지만, 그 후 반격이 강해요!",
                "BRV 흡수 패턴이 있어요. 너무 많이 쌓아두면 위험!",
            ],
            "dragon": [
                "드래곤은 브레스 공격 전에 '숨을 들이마신다' 메시지가 나와요!",
                "비행 상태에선 근접 공격 불가! 원거리/마법 사용!",
                "꼬리 공격은 후열 타겟, 진형 관리 중요!",
            ],
            "demon_king": [
                "마왕은 HP 50% 이하에서 2회 행동해요!",
                "어둠 속성 공격 특화, 빛 속성에 약해요!",
                "소환수를 부르면 먼저 처리하세요!",
            ],
            "default": [
                "보스 패턴을 관찰하세요! 강공격 전에 힌트가 있어요.",
                "힐러는 HP 관리에 집중! 딜러는 BREAK 노리기!",
                "위험하면 도망도 전략이에요!",
            ],
        }
        
        return boss_strategies.get(boss_id, boss_strategies["default"])
    
    def _add_custom_message(self, text: str, priority: int = 0, 
                           personality: BotPersonality = BotPersonality.SELENA):
        """커스텀 메시지 추가"""
        message = BotMessage(
            text=text,
            personality=personality,
            priority=priority,
            duration=4.0,
            category="custom"
        )
        self.message_queue.append(message)
    
    def say(self, text: str, personality: BotPersonality = BotPersonality.SELENA):
        """즉시 메시지 표시 (편의 함수)"""
        self._add_custom_message(text, priority=10, personality=personality)
    
    # =========================================================================
    # 아이템/스킬 추천
    # =========================================================================
    
    def recommend_action(
        self,
        character: Any,
        enemies: List[Any],
        available_skills: List[str] = None
    ) -> str:
        """
        현재 상황에서 추천 행동
        
        Returns:
            추천 행동 설명
        """
        char_brv = getattr(character, 'current_brv', 0)
        char_max_brv = getattr(character, 'max_brv', 1000)
        char_hp_pct = getattr(character, 'current_hp', 100) / max(getattr(character, 'max_hp', 100), 1)
        
        # BRV 상태 분석
        brv_ratio = char_brv / max(char_max_brv, 1)
        
        if brv_ratio >= 0.8:
            return "💡 BRV가 충분해요! HP 공격 추천!"
        
        if brv_ratio <= 0.2:
            return "💡 BRV가 낮아요! BRV 공격으로 쌓으세요!"
        
        # 적 상태 분석
        for enemy in enemies:
            enemy_brv = getattr(enemy, 'current_brv', 100)
            if enemy_brv <= 30:
                return f"💡 적 BRV가 낮아요! BRV 공격으로 BREAK!"
        
        # HP 낮으면
        if char_hp_pct <= 0.3:
            return "💡 HP가 낮아요! 회복하거나 조심하세요!"
        
        return "💡 BRV를 쌓고 적절한 타이밍에 HP 공격!"
    
    # =========================================================================
    # 시스템 지식 조회 (요리, 채집, 오브젝트 등)
    # =========================================================================
    
    def explain_object(self, object_id: str) -> str:
        """
        던전 오브젝트 설명
        
        Args:
            object_id: 오브젝트 ID 또는 심볼
        
        Returns:
            설명 문자열
        """
        # ID로 검색
        if object_id in DUNGEON_OBJECTS:
            obj = DUNGEON_OBJECTS[object_id]
            return f"{obj['name']}: {obj['tips']}"
        
        # 심볼로 검색
        for obj_id, obj in DUNGEON_OBJECTS.items():
            if obj.get("symbol") == object_id:
                return f"{obj['name']}: {obj['tips']}"
        
        return "알 수 없는 오브젝트예요."
    
    def explain_cooking(self, recipe_id: str = None) -> str:
        """
        요리 설명
        
        Args:
            recipe_id: 레시피 ID (없으면 일반 팁)
        
        Returns:
            설명 문자열
        """
        if recipe_id and recipe_id in COOKING_DATABASE:
            recipe = COOKING_DATABASE[recipe_id]
            ingredients = ", ".join(recipe["ingredients"])
            return f"{recipe['name']}: {recipe['effect']} (재료: {ingredients})"
        
        return random.choice(COOKING_TIPS)
    
    def explain_gathering(self, spot_type: str = None) -> str:
        """
        채집 설명
        
        Args:
            spot_type: 채집 포인트 유형 (없으면 일반 팁)
        
        Returns:
            설명 문자열
        """
        if spot_type and spot_type in GATHERING_DATABASE:
            spot = GATHERING_DATABASE[spot_type]
            drops = ", ".join(spot["drops"][:3])
            return f"{spot['name']}: {spot['tips']} (드랍: {drops})"
        
        return random.choice(GATHERING_TIPS)
    
    def explain_status(self, status_id: str) -> str:
        """
        상태이상/버프 설명
        
        Args:
            status_id: 상태 ID
        
        Returns:
            설명 문자열
        """
        if status_id in STATUS_EFFECTS:
            status = STATUS_EFFECTS[status_id]
            cure = status.get("cure", "시간 경과")
            return f"{status['name']}: {status['effect']} (해제: {cure})"
        
        return random.choice(STATUS_TIPS)
    
    def explain_equipment(self, equip_type: str = None) -> str:
        """
        장비 설명
        
        Args:
            equip_type: 장비 유형 (weapon, armor, accessory)
        
        Returns:
            설명 문자열
        """
        if equip_type and equip_type in EQUIPMENT_DATABASE:
            equip = EQUIPMENT_DATABASE[equip_type]
            tip = random.choice(equip["tips"])
            return f"{equip['name']}: {tip}"
        
        return random.choice(EQUIPMENT_TIPS)
    
    def get_cooking_recommendation(self, situation: str = "boss") -> str:
        """
        상황별 요리 추천
        
        Args:
            situation: 상황 (boss, healing, buff, resistance)
        
        Returns:
            추천 요리 설명
        """
        recommendations = {
            "boss": [
                "보스전엔 '전사의 스테이크'로 공격력 버프!",
                "보스전엔 '부활의 파이'로 보험을 들어두세요!",
                "'강철 스프'로 탱커 방어력 올려요!",
            ],
            "healing": [
                "'왕실 스튜'가 최고의 회복 요리예요!",
                "'치유 허브 스프'는 재료도 쉽고 효과도 좋아요!",
                "'생존의 빵'으로 지속 회복!",
            ],
            "buff": [
                "'신속의 면'으로 속도 버프!",
                "'치명타 케이크'로 딜러 크리티컬 UP!",
                "'마법사의 차'는 마법 직업 필수!",
            ],
            "resistance": [
                "화염 보스엔 '화염 저항 스튜'!",
                "독 보스엔 '해독 샐러드'!",
            ],
        }
        
        tips = recommendations.get(situation, recommendations["boss"])
        return random.choice(tips)
    
    def on_object_interact(self, object_id: str):
        """
        오브젝트 상호작용 시 조언
        
        Args:
            object_id: 오브젝트 ID
        """
        if not self.enabled:
            return
        
        obj = DUNGEON_OBJECTS.get(object_id)
        if not obj:
            return
        
        # 위험한 오브젝트 경고
        if obj.get("trap_chance", 0) > 0.3:
            self.say(f"⚠️ {obj['name']}! {obj['tips']}", BotPersonality.KARNOS)
        # 유용한 오브젝트 안내
        elif object_id in ["healing_fountain", "save_point", "mana_crystal"]:
            self.say(f"✨ {obj['name']} 발견! {obj['tips']}", BotPersonality.MIRA)
        # 상인/NPC
        elif object_id in ["merchant", "healer_npc", "info_npc"]:
            self.say(f"👤 {obj['name']}! {obj['tips']}", BotPersonality.SELENA)
    
    def on_gather_spot(self, spot_type: str):
        """
        채집 포인트 발견 시 조언
        
        Args:
            spot_type: 채집 포인트 유형
        """
        if not self.enabled:
            return
        
        spot = GATHERING_DATABASE.get(spot_type)
        if spot:
            drops = ", ".join(spot["drops"][:2])
            self.say(f"🌿 {spot['name']}! ({drops} 등)", BotPersonality.MIRA)
    
    def on_status_effect(self, status_id: str, is_ally: bool = True):
        """
        상태이상 발생 시 조언
        
        Args:
            status_id: 상태 ID
            is_ally: 아군 여부
        """
        if not self.enabled:
            return
        
        status = STATUS_EFFECTS.get(status_id)
        if not status:
            return
        
        # 아군 디버프
        if is_ally and "cure" in status:
            cure = status["cure"]
            self.say(f"⚠️ {status['name']} 상태! 해제: {cure}", BotPersonality.SELENA)
    
    def get_meta_advice(self) -> str:
        """
        메타 프로그레션 조언
        
        Returns:
            조언 문자열
        """
        tips = META_PROGRESSION["stellar_fragments"]["tips"]
        return random.choice(tips)
    
    # =========================================================================
    # 통합 질문 응답 시스템
    # =========================================================================
    
    def answer_question(self, question: str) -> str:
        """
        플레이어 질문에 응답 (키워드 기반)
        
        Args:
            question: 질문 문자열
        
        Returns:
            응답 문자열
        """
        question = question.lower()
        
        # 직업 관련
        for job_id, job_data in JOB_DATABASE.items():
            if job_data["name"] in question or job_id in question:
                tip = random.choice(job_data["tips"])
                return f"{job_data['name']}({job_data['role']}): {tip}"
        
        # 요리 관련
        if "요리" in question or "음식" in question or "cook" in question:
            return self.get_cooking_recommendation()
        
        # 채집 관련
        if "채집" in question or "수집" in question or "gather" in question:
            return random.choice(GATHERING_TIPS)
        
        # 장비 관련
        if "장비" in question or "무기" in question or "갑옷" in question:
            return random.choice(EQUIPMENT_TIPS)
        
        # 상태이상 관련
        if "상태" in question or "독" in question or "마비" in question:
            return random.choice(STATUS_TIPS)
        
        # BRV/HP 관련
        if "brv" in question or "브레이브" in question:
            return "BRV 공격으로 용기치를 쌓고, HP 공격으로 실제 피해를 줘요!"
        
        if "break" in question or "브레이크" in question:
            return "적 BRV를 0으로 만들면 BREAK! 보너스 데미지 + 스턴!"
        
        # 별의 파편
        if "별" in question or "파편" in question or "해금" in question:
            return self.get_meta_advice()
        
        # 보스 관련
        if "보스" in question:
            strategies = self.get_boss_strategy("default")
            return random.choice(strategies)
        
        # 기본 응답
        return "무엇이든 물어보세요! 직업, 요리, 채집, 장비, 전투 등!"


# =============================================================================
# 전역 봇 인스턴스
# =============================================================================

_tutorial_bot: Optional[TutorialBot] = None


def get_tutorial_bot() -> TutorialBot:
    """튜토리얼 봇 싱글톤 반환"""
    global _tutorial_bot
    if _tutorial_bot is None:
        _tutorial_bot = TutorialBot()
    return _tutorial_bot


def reset_tutorial_bot():
    """튜토리얼 봇 리셋"""
    global _tutorial_bot
    _tutorial_bot = TutorialBot()
    return _tutorial_bot
